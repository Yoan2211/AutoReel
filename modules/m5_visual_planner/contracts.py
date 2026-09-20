import hashlib
import json
from importlib.resources import files
from pathlib import Path

from .errors import VisualPlannerError
from .time_mapping import validate_mappings


def validate(value, schema_name):
    try:
        from jsonschema import Draft202012Validator
    except ImportError as exc:
        raise VisualPlannerError('Install contracts with pip install -e ".[test]"') from exc
    schema = json.loads(files("core").joinpath("schemas", schema_name).read_text(encoding="utf-8-sig"))
    error = next(Draft202012Validator(schema).iter_errors(value), None)
    if error:
        raise VisualPlannerError(f"Invalid {schema_name} at {list(error.path)}: {error.message}")
    if schema_name == "visual-plan-1.0.0.json":
        for request in value["requests"]:
            if request["source_start_us"] >= request["source_end_us"]:
                raise VisualPlannerError("Visual request has an empty or reversed SOURCE interval")
            cut_start, cut_end = request["cut_start_us"], request["cut_end_us"]
            if (cut_start is None) != (cut_end is None):
                raise VisualPlannerError("Visual request CUT bounds must both be present or absent")
            if cut_start is not None and cut_start >= cut_end:
                raise VisualPlannerError("Visual request has an empty or reversed CUT interval")
            if request["disposition"] != "NONE" and request["desired_duration_us"] != cut_end - cut_start:
                raise VisualPlannerError("Visual request duration disagrees with CUT interval")


def read(path, schema_name):
    raw = path.read_bytes()
    try:
        value = json.loads(raw.decode("utf-8-sig"), parse_constant=lambda item: (_ for _ in ()).throw(VisualPlannerError(f"Non-finite JSON: {item}")))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise VisualPlannerError(f"Invalid JSON: {path}") from exc
    validate(value, schema_name)
    return value, hashlib.sha256(raw).hexdigest()


def load_inputs(edit_path, transcript_path, map_path, camera_path=None):
    edit, edit_hash = read(edit_path, "edit-plan-1.0.0.json")
    transcript, transcript_hash = read(transcript_path, "transcript-1.0.0.json")
    time_map, map_hash = read(map_path, "time-map-smartedit-1.0.0.json")
    if edit["source"]["transcript_sha256"] != transcript_hash:
        raise VisualPlannerError("edit_plan.json does not reference the supplied transcript")
    if time_map["source"]["transcript_sha256"] != transcript_hash:
        raise VisualPlannerError("time_map.json does not reference the supplied transcript")
    if time_map["source"]["edit_plan_sha256"] != edit_hash:
        raise VisualPlannerError("time_map.json does not reference the supplied edit_plan.json")
    identities = {transcript["source"]["sha256"], edit["source"]["media_sha256"], time_map["source"]["media_sha256"]}
    if len(identities) != 1:
        raise VisualPlannerError("Input media identities disagree")
    validate_mappings(time_map["mappings"], time_map["output_duration_us"])
    passage_ids = {item["id"] for item in edit["passages"]}
    word_ids = {word["id"] for segment in transcript["segments"] for word in segment["words"]}
    if any(not set(item["word_ids"]) <= word_ids for item in edit["passages"]):
        raise VisualPlannerError("edit_plan.json references unknown transcript words")
    if any(not set(item["passage_ids"]) <= passage_ids for item in edit["sections"]):
        raise VisualPlannerError("edit_plan.json section references unknown passages")
    camera = camera_hash = None
    if camera_path is not None:
        camera, camera_hash = read(camera_path, "camera-plan-1.0.0.json")
        if camera["source"]["smartedit_time_map_sha256"] != map_hash:
            raise VisualPlannerError("camera_plan.json does not reference the supplied SmartEdit map")
        if camera["source"]["media_sha256"] not in identities:
            raise VisualPlannerError("camera_plan.json media identity disagrees")
    return edit, transcript, time_map, camera, edit_hash, transcript_hash, map_hash, camera_hash
