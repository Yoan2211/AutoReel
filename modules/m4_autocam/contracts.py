import hashlib, json
from importlib.resources import files
from pathlib import Path

from .errors import AutoCamError


def validate(value, schema_name):
    from jsonschema import Draft202012Validator
    schema = json.loads(files("core").joinpath("schemas", schema_name).read_text(encoding="utf-8-sig"))
    error = next(Draft202012Validator(schema).iter_errors(value), None)
    if error: raise AutoCamError(f"Invalid {schema_name} at {list(error.path)}: {error.message}")


def read(path, schema):
    raw = path.read_bytes()
    try: value = json.loads(raw.decode("utf-8-sig"), parse_constant=lambda x: (_ for _ in ()).throw(AutoCamError(f"Non-finite JSON: {x}")))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc: raise AutoCamError(f"Invalid JSON: {path}") from exc
    validate(value, schema); return value, hashlib.sha256(raw).hexdigest()


def load_inputs(manifest_path, map_path):
    manifest, manifest_hash = read(manifest_path, "source-manifest-1.0.0.json")
    time_map, map_hash = read(map_path, "time-map-smartedit-1.0.0.json")
    source = manifest["source"]
    if source["sha256"] != time_map["source"]["media_sha256"] or source["path"] != time_map["source"]["media_path"]:
        raise AutoCamError("M0 source and M3 time map media identities disagree")
    previous_end = None
    for item in time_map["mappings"]:
        start, end = item["source"]["start_us"], item["source"]["end_us"]
        if start >= end or (previous_end is not None and start < previous_end):
            raise AutoCamError("M3 SOURCE intervals overlap or are invalid")
        previous_end = end
    return manifest, time_map, manifest_hash, map_hash


def verify_media(source):
    path = Path(source["path"])
    if not path.is_file() or path.stat().st_size != source["size_bytes"]:
        raise AutoCamError("Original SOURCE file is missing or changed")
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024*1024), b""): digest.update(block)
    if digest.hexdigest() != source["sha256"]: raise AutoCamError("Original SOURCE hash no longer matches M0")
    stat = path.stat()
    return path, (stat.st_size, stat.st_mtime_ns, stat.st_ino)
