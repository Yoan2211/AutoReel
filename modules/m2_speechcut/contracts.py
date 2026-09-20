"""M2 JSON contract boundary, independent from M1 implementation."""

import hashlib
from importlib.resources import files
import json
from pathlib import Path

from .errors import SpeechCutError


def _reject_constant(value: str):
    raise SpeechCutError(f"Non-finite JSON value: {value}")


def load_json(path: Path) -> tuple[dict, str]:
    raw = path.read_bytes()
    try:
        value = json.loads(raw.decode("utf-8-sig"), parse_constant=_reject_constant)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise SpeechCutError(f"Invalid JSON: {path}") from exc
    return value, hashlib.sha256(raw).hexdigest()


def validate(value: dict, schema_name: str) -> None:
    try:
        from jsonschema import Draft202012Validator
    except ImportError as exc:
        raise SpeechCutError('Install test contracts: pip install -e ".[test]"') from exc
    schema = json.loads(files("core").joinpath("schemas", schema_name).read_text(encoding="utf-8-sig"))
    error = next(Draft202012Validator(schema).iter_errors(value), None)
    if error:
        raise SpeechCutError(f"Invalid {schema_name} at {list(error.path)}: {error.message}")


def load_transcript(path: Path) -> tuple[dict, str]:
    value, digest = load_json(path)
    validate(value, "transcript-1.0.0.json")
    if value["time_domain"] != "SOURCE":
        raise SpeechCutError("M2 requires a SOURCE transcript")
    return value, digest
