import hashlib
import json
from importlib.resources import files

from core.timeline import validate_source_cut_map

from .errors import MusicPlannerError


def validate(value, schema_name):
    try:
        from jsonschema import Draft202012Validator
    except ImportError as exc:
        raise MusicPlannerError('Install contracts with pip install -e ".[test]"') from exc
    schema = json.loads(files("core").joinpath("schemas", schema_name).read_text(encoding="utf-8-sig"))
    error = next(Draft202012Validator(schema).iter_errors(value), None)
    if error:
        raise MusicPlannerError(f"Invalid {schema_name} at {list(error.path)}: {error.message}")
    if schema_name == "music-plan-1.0.0.json":
        for region in value["regions"]:
            if region["cut_start_us"] >= region["cut_end_us"]:
                raise MusicPlannerError("Music region has an empty or reversed CUT interval")
            if any(item["source_start_us"] >= item["source_end_us"] for item in region["source_intervals"]):
                raise MusicPlannerError("Music region has an invalid SOURCE interval")
        for region in value["level_regions"]:
            if region["cut_start_us"] >= region["cut_end_us"]:
                raise MusicPlannerError("Music level region has an empty or reversed CUT interval")
            if any(item["source_start_us"] >= item["source_end_us"] for item in region["source_intervals"]):
                raise MusicPlannerError("Music level region has an invalid SOURCE interval")
        levels = value["level_regions"]
        if levels:
            if levels[0]["cut_start_us"] != 0 or any(left["cut_end_us"] != right["cut_start_us"] for left, right in zip(levels, levels[1:])):
                raise MusicPlannerError("Music level regions must cover CUT contiguously")
            if not value["regions"] or levels[-1]["cut_end_us"] != value["regions"][-1]["cut_end_us"]:
                raise MusicPlannerError("Music level regions do not cover the music region")
        summary = value["summary"]
        expected = {"music_region_count": len(value["regions"]), "level_region_count": len(levels),
                    "speech_duck_count": sum(item["mode"] == "SPEECH_DUCK" for item in levels),
                    "no_speech_lift_count": sum(item["mode"] == "NO_SPEECH_LIFT" for item in levels),
                    "sfx_protected_count": sum(item["mode"] == "SFX_PROTECTED" for item in levels)}
        if summary != expected:
            raise MusicPlannerError("Music plan summary disagrees with regions")


def read(path, schema_name):
    raw = path.read_bytes()
    try:
        value = json.loads(raw.decode("utf-8-sig"), parse_constant=lambda item: (_ for _ in ()).throw(MusicPlannerError(f"Non-finite JSON: {item}")))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise MusicPlannerError(f"Invalid JSON: {path}") from exc
    validate(value, schema_name)
    return value, hashlib.sha256(raw).hexdigest()


def load_inputs(transcript_path, edit_path, map_path, visual_path, sound_path):
    transcript, transcript_hash = read(transcript_path, "transcript-1.0.0.json")
    edit, edit_hash = read(edit_path, "edit-plan-1.0.0.json")
    time_map, map_hash = read(map_path, "time-map-smartedit-1.0.0.json")
    visual, visual_hash = read(visual_path, "visual-plan-1.0.0.json")
    sound, sound_hash = read(sound_path, "sound-plan-1.0.0.json")
    if edit["source"]["transcript_sha256"] != transcript_hash:
        raise MusicPlannerError("edit_plan.json does not reference the supplied transcript")
    if time_map["source"]["transcript_sha256"] != transcript_hash or time_map["source"]["edit_plan_sha256"] != edit_hash:
        raise MusicPlannerError("SmartEdit map input provenance disagrees")
    if visual["source"]["transcript_sha256"] != transcript_hash or visual["source"]["edit_plan_sha256"] != edit_hash or visual["source"]["smartedit_time_map_sha256"] != map_hash:
        raise MusicPlannerError("visual_plan.json input provenance disagrees")
    if sound["source"]["transcript_sha256"] != transcript_hash or sound["source"]["edit_plan_sha256"] != edit_hash or sound["source"]["visual_plan_sha256"] != visual_hash or sound["source"]["smartedit_time_map_sha256"] != map_hash:
        raise MusicPlannerError("sound_plan.json input provenance disagrees")
    identities = {transcript["source"]["sha256"], edit["source"]["media_sha256"],
                  visual["source"]["media_sha256"], sound["source"]["media_sha256"],
                  time_map["source"]["media_sha256"]}
    if len(identities) != 1:
        raise MusicPlannerError("Input media identities disagree")
    validate_source_cut_map(time_map["mappings"], time_map["output_duration_us"], MusicPlannerError)
    return transcript, edit, time_map, visual, sound, {
        "transcript_sha256": transcript_hash, "edit_plan_sha256": edit_hash,
        "smartedit_time_map_sha256": map_hash, "visual_plan_sha256": visual_hash,
        "sound_plan_sha256": sound_hash}
