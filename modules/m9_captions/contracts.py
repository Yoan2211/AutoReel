import hashlib
import json
from importlib.resources import files
from pathlib import Path

from .errors import CaptionsError


def validate(value, schema_name):
    try:
        from jsonschema import Draft202012Validator
    except ImportError as exc:
        raise CaptionsError('Install contracts with pip install -e ".[test]"') from exc
    schema = json.loads(files("core").joinpath("schemas", schema_name).read_text(encoding="utf-8-sig"))
    error = next(Draft202012Validator(schema).iter_errors(value), None)
    if error:
        raise CaptionsError(f"Invalid {schema_name} at {list(error.path)}: {error.message}")


def read(path, schema_name):
    raw = path.read_bytes()
    try:
        value = json.loads(raw.decode("utf-8-sig"), parse_constant=lambda item: (_ for _ in ()).throw(
            CaptionsError(f"Non-finite JSON: {item}")))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise CaptionsError(f"Invalid JSON: {path}") from exc
    validate(value, schema_name)
    return value, hashlib.sha256(raw).hexdigest()


def load_inputs(transcript_path, timeline_path):
    transcript_path = Path(transcript_path).resolve(strict=True)
    timeline_path = Path(timeline_path).resolve(strict=True)
    transcript, transcript_hash = read(transcript_path, "transcript-1.0.0.json")
    timeline, timeline_hash = read(timeline_path, "timeline-draft-1.0.0.json")
    edit_path = Path(timeline["source"]["edit_plan_path"]).resolve(strict=True)
    raw = edit_path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != timeline["source"]["edit_plan_sha256"]:
        raise CaptionsError("Timeline edit-plan provenance changed")
    try:
        edit = json.loads(raw.decode("utf-8-sig"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise CaptionsError("Timeline references an invalid edit plan") from exc
    validate(edit, "edit-plan-1.0.0.json")
    if edit["source"]["transcript_sha256"] != transcript_hash:
        raise CaptionsError("Timeline provenance does not reference the supplied transcript")
    v1 = next((item for item in timeline["tracks"] if item["id"] == "V1"), None)
    if v1 is None:
        raise CaptionsError("Timeline has no V1 track")
    if any(event["type"] != "SOURCE_VIDEO" for event in v1["events"]):
        raise CaptionsError("Timeline V1 contains an invalid event type")
    media_hashes = {event["media_sha256"] for event in v1["events"]}
    if media_hashes and media_hashes != {transcript["source"]["sha256"]}:
        raise CaptionsError("Transcript and timeline SOURCE identities disagree")
    return transcript, timeline, transcript_hash, timeline_hash, transcript_path, timeline_path


def validate_captions(value):
    validate(value, "captions-1.0.0.json")
    captions = value["captions"]
    if any(left["timeline_end_us"] > right["timeline_start_us"] for left, right in zip(captions, captions[1:])):
        raise CaptionsError("Captions overlap or are unordered")
    if value["summary"]["caption_count"] != len(captions):
        raise CaptionsError("Caption summary disagrees with contents")
