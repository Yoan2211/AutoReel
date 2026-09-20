import hashlib
from importlib.resources import files
import json
from pathlib import Path

from .errors import SmartEditError


def _reject(value: str):
    raise SmartEditError(f"Non-finite JSON value: {value}")


def read_json(path: Path, schema: str) -> tuple[dict, str]:
    raw = path.read_bytes()
    try:
        value = json.loads(raw.decode("utf-8-sig"), parse_constant=_reject)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise SmartEditError(f"Invalid JSON: {path}") from exc
    validate(value, schema)
    return value, hashlib.sha256(raw).hexdigest()


def validate(value: dict, schema_name: str) -> None:
    try:
        from jsonschema import Draft202012Validator
    except ImportError as exc:
        raise SmartEditError('Install contracts with pip install -e ".[test]"') from exc
    schema = json.loads(files("core").joinpath("schemas", schema_name).read_text(encoding="utf-8-sig"))
    error = next(Draft202012Validator(schema).iter_errors(value), None)
    if error:
        raise SmartEditError(f"Invalid {schema_name} at {list(error.path)}: {error.message}")


def load_inputs(transcript_path: Path, cuts_path: Path, time_map_path: Path):
    transcript, transcript_hash = read_json(transcript_path, "transcript-1.0.0.json")
    cuts, cuts_hash = read_json(cuts_path, "cuts-1.0.0.json")
    time_map, map_hash = read_json(time_map_path, "time-map-speechcut-1.0.0.json")
    if cuts["source"]["transcript_sha256"] != transcript_hash:
        raise SmartEditError("cuts.json does not reference the supplied transcript")
    if time_map["source"]["transcript_sha256"] != transcript_hash:
        raise SmartEditError("time_map.json does not reference the supplied transcript")
    if time_map["source"]["cuts_sha256"] != cuts_hash:
        raise SmartEditError("time_map.json does not reference the supplied cuts.json")
    hashes = {transcript["source"]["sha256"], cuts["source"]["media_sha256"],
              time_map["source"]["media_sha256"]}
    if len(hashes) != 1:
        raise SmartEditError("Input media identities disagree")
    _validate_map(time_map)
    return transcript, cuts, time_map, transcript_hash, cuts_hash, map_hash


def _validate_map(time_map: dict) -> None:
    source_cursor = None
    target_cursor = 0
    for mapping in time_map["mappings"]:
        source, target = mapping["source"], mapping["target"]
        if source["start_us"] >= source["end_us"] or target["start_us"] >= target["end_us"]:
            raise SmartEditError("Time map contains an empty or reversed interval")
        if source_cursor is not None and source["start_us"] < source_cursor:
            raise SmartEditError("Time map SOURCE intervals overlap or are unordered")
        if target["start_us"] != target_cursor:
            raise SmartEditError("Time map CUT intervals are not contiguous")
        if source["end_us"] - source["start_us"] != target["end_us"] - target["start_us"]:
            raise SmartEditError("Time map changes speed")
        source_cursor, target_cursor = source["end_us"], target["end_us"]
    if target_cursor != time_map["output_duration_us"]:
        raise SmartEditError("Time map duration disagrees with mappings")
