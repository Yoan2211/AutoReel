import hashlib
import json
from importlib.resources import files

from core.timeline import validate_source_cut_map

from .errors import SoundDesignError


def validate(value, schema_name):
    try:
        from jsonschema import Draft202012Validator
    except ImportError as exc:
        raise SoundDesignError('Install contracts with pip install -e ".[test]"') from exc
    schema = json.loads(files("core").joinpath("schemas", schema_name).read_text(encoding="utf-8-sig"))
    error = next(Draft202012Validator(schema).iter_errors(value), None)
    if error:
        raise SoundDesignError(f"Invalid {schema_name} at {list(error.path)}: {error.message}")
    if schema_name == "sound-plan-1.0.0.json":
        summary = value["summary"]
        if summary["candidate_count"] != len(value["decisions"]):
            raise SoundDesignError("Sound plan candidate count disagrees with decisions")
        for status, key in (("PROPOSED", "proposed_count"), ("REVIEW", "review_count"), ("NONE", "none_count")):
            if summary[key] != sum(item["status"] == status for item in value["decisions"]):
                raise SoundDesignError(f"Sound plan {key} disagrees with decisions")


def read(path, schema_name):
    raw = path.read_bytes()
    try:
        value = json.loads(raw.decode("utf-8-sig"), parse_constant=lambda item: (_ for _ in ()).throw(SoundDesignError(f"Non-finite JSON: {item}")))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise SoundDesignError(f"Invalid JSON: {path}") from exc
    validate(value, schema_name)
    return value, hashlib.sha256(raw).hexdigest()


def load_inputs(transcript_path, edit_path, visual_path, camera_path, map_path):
    transcript, transcript_hash = read(transcript_path, "transcript-1.0.0.json")
    edit, edit_hash = read(edit_path, "edit-plan-1.0.0.json")
    visual, visual_hash = read(visual_path, "visual-plan-1.0.0.json")
    camera, camera_hash = read(camera_path, "camera-plan-1.0.0.json")
    time_map, map_hash = read(map_path, "time-map-smartedit-1.0.0.json")
    if edit["source"]["transcript_sha256"] != transcript_hash:
        raise SoundDesignError("edit_plan.json does not reference the supplied transcript")
    if time_map["source"]["transcript_sha256"] != transcript_hash or time_map["source"]["edit_plan_sha256"] != edit_hash:
        raise SoundDesignError("SmartEdit map input provenance disagrees")
    if visual["source"]["transcript_sha256"] != transcript_hash or visual["source"]["edit_plan_sha256"] != edit_hash or visual["source"]["smartedit_time_map_sha256"] != map_hash:
        raise SoundDesignError("visual_plan.json input provenance disagrees")
    if camera["source"]["smartedit_time_map_sha256"] != map_hash:
        raise SoundDesignError("camera_plan.json does not reference the supplied SmartEdit map")
    if visual["source"]["camera_plan_sha256"] is not None and visual["source"]["camera_plan_sha256"] != camera_hash:
        raise SoundDesignError("visual_plan.json references a different camera plan")
    identities = {transcript["source"]["sha256"], edit["source"]["media_sha256"],
                  visual["source"]["media_sha256"], camera["source"]["media_sha256"],
                  time_map["source"]["media_sha256"]}
    if len(identities) != 1:
        raise SoundDesignError("Input media identities disagree")
    validate_source_cut_map(time_map["mappings"], time_map["output_duration_us"], SoundDesignError)
    return transcript, edit, visual, camera, time_map, {
        "transcript_sha256": transcript_hash, "edit_plan_sha256": edit_hash,
        "visual_plan_sha256": visual_hash, "camera_plan_sha256": camera_hash,
        "smartedit_time_map_sha256": map_hash}
