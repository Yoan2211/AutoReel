import hashlib
import json
from importlib.resources import files

from .errors import AssetManagerError


def validate(value, schema_name):
    try:
        from jsonschema import Draft202012Validator
    except ImportError as exc:
        raise AssetManagerError('Install contracts with pip install -e ".[test]"') from exc
    schema = json.loads(files("core").joinpath("schemas", schema_name).read_text(encoding="utf-8-sig"))
    error = next(Draft202012Validator(schema).iter_errors(value), None)
    if error:
        raise AssetManagerError(f"Invalid {schema_name} at {list(error.path)}: {error.message}")
    if schema_name == "assets-manifest-1.0.0.json":
        asset_ids = {item["asset_id"] for item in value["assets"]}
        if len(asset_ids) != len(value["assets"]):
            raise AssetManagerError("Asset IDs must be unique")
        for request in value["requests"]:
            if request["asset_id"] is not None and request["asset_id"] not in asset_ids:
                raise AssetManagerError("Request references an unknown asset")
        summary = value["summary"]
        expected = {"request_count": len(value["requests"]), "resolved_count": sum(item["status"] == "RESOLVED" for item in value["requests"]),
                    "review_count": sum(item["status"] == "REVIEW" for item in value["requests"]),
                    "unresolved_count": sum(item["status"] == "UNRESOLVED" for item in value["requests"]),
                    "unique_asset_count": len(value["assets"]), "library_issue_count": len(value["library_issues"])}
        if summary != expected:
            raise AssetManagerError("Asset manifest summary disagrees with contents")


def read(path, schema_name):
    raw = path.read_bytes()
    try:
        value = json.loads(raw.decode("utf-8-sig"), parse_constant=lambda item: (_ for _ in ()).throw(AssetManagerError(f"Non-finite JSON: {item}")))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise AssetManagerError(f"Invalid JSON: {path}") from exc
    validate(value, schema_name)
    return value, hashlib.sha256(raw).hexdigest()


def load_inputs(visual_path, sound_path, music_path):
    visual, visual_hash = read(visual_path, "visual-plan-1.0.0.json")
    sound, sound_hash = read(sound_path, "sound-plan-1.0.0.json")
    music, music_hash = read(music_path, "music-plan-1.0.0.json")
    if sound["source"]["visual_plan_sha256"] != visual_hash:
        raise AssetManagerError("sound_plan.json does not reference the supplied visual plan")
    if music["source"]["visual_plan_sha256"] != visual_hash or music["source"]["sound_plan_sha256"] != sound_hash:
        raise AssetManagerError("music_plan.json input provenance disagrees")
    identities = {visual["source"]["media_sha256"], sound["source"]["media_sha256"], music["source"]["media_sha256"]}
    if len(identities) != 1:
        raise AssetManagerError("Input media identities disagree")
    return visual, sound, music, {"visual_plan_sha256": visual_hash,
                                  "sound_plan_sha256": sound_hash,
                                  "music_plan_sha256": music_hash}
