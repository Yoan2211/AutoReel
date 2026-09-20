import hashlib
import json
from importlib.resources import files
from pathlib import Path

from core.timeline import validate_source_cut_map

from .errors import TimelineCompilerError


SCHEMAS = (
    "source-manifest-1.0.0.json", "time-map-smartedit-1.0.0.json",
    "edit-plan-1.0.0.json", "camera-plan-1.0.0.json", "visual-plan-1.0.0.json",
    "sound-plan-1.0.0.json", "music-plan-1.0.0.json", "assets-manifest-1.0.0.json")


def validate(value, schema_name):
    try:
        from jsonschema import Draft202012Validator
    except ImportError as exc:
        raise TimelineCompilerError('Install contracts with pip install -e ".[test]"') from exc
    schema = json.loads(files("core").joinpath("schemas", schema_name).read_text(encoding="utf-8-sig"))
    error = next(Draft202012Validator(schema).iter_errors(value), None)
    if error:
        raise TimelineCompilerError(f"Invalid {schema_name} at {list(error.path)}: {error.message}")


def _read(path, schema):
    raw = path.read_bytes()
    try:
        value = json.loads(raw.decode("utf-8-sig"), parse_constant=lambda item: (_ for _ in ()).throw(
            TimelineCompilerError(f"Non-finite JSON: {item}")))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise TimelineCompilerError(f"Invalid JSON: {path}") from exc
    validate(value, schema)
    return value, hashlib.sha256(raw).hexdigest()


def load_inputs(paths):
    resolved = [Path(item).resolve(strict=True) for item in paths]
    loaded = [_read(path, schema) for path, schema in zip(resolved, SCHEMAS)]
    values = [item[0] for item in loaded]
    hashes = [item[1] for item in loaded]
    media, time_map, edit, camera, visual, sound, music, assets = values
    media_hash, map_hash, edit_hash, camera_hash, visual_hash, sound_hash, music_hash, _ = hashes

    if time_map["source"]["edit_plan_sha256"] != edit_hash:
        raise TimelineCompilerError("M3 map does not reference the supplied edit plan")
    if camera["source"]["manifest_sha256"] != media_hash or camera["source"]["smartedit_time_map_sha256"] != map_hash:
        raise TimelineCompilerError("Camera plan provenance disagrees")
    if visual["source"]["edit_plan_sha256"] != edit_hash or visual["source"]["smartedit_time_map_sha256"] != map_hash:
        raise TimelineCompilerError("Visual plan provenance disagrees")
    if visual["source"]["camera_plan_sha256"] != camera_hash:
        raise TimelineCompilerError("Visual plan does not reference the supplied camera plan")
    if sound["source"]["edit_plan_sha256"] != edit_hash or sound["source"]["visual_plan_sha256"] != visual_hash or sound["source"]["camera_plan_sha256"] != camera_hash or sound["source"]["smartedit_time_map_sha256"] != map_hash:
        raise TimelineCompilerError("Sound plan provenance disagrees")
    if music["source"]["edit_plan_sha256"] != edit_hash or music["source"]["visual_plan_sha256"] != visual_hash or music["source"]["sound_plan_sha256"] != sound_hash or music["source"]["smartedit_time_map_sha256"] != map_hash:
        raise TimelineCompilerError("Music plan provenance disagrees")
    if assets["source"]["visual_plan_sha256"] != visual_hash or assets["source"]["sound_plan_sha256"] != sound_hash or assets["source"]["music_plan_sha256"] != music_hash:
        raise TimelineCompilerError("Assets manifest provenance disagrees")
    identities = {media["source"]["sha256"], time_map["source"]["media_sha256"],
                  edit["source"]["media_sha256"], camera["source"]["media_sha256"],
                  visual["source"]["media_sha256"], sound["source"]["media_sha256"],
                  music["source"]["media_sha256"], assets["source"]["media_sha256"]}
    if len(identities) != 1:
        raise TimelineCompilerError("Input media identities disagree")
    if assets["source"]["media_path"] != media["source"]["path"]:
        raise TimelineCompilerError("Assets manifest media path disagrees")
    if any(value["source"]["media_path"] != media["source"]["path"] for value in
           (time_map, edit, camera, visual, sound, music)):
        raise TimelineCompilerError("Input media paths disagree")
    validate_source_cut_map(time_map["mappings"], time_map["output_duration_us"], TimelineCompilerError)
    return values, resolved, hashes


def validate_draft(value):
    validate(value, "timeline-draft-1.0.0.json")
