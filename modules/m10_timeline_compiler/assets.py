import hashlib
from pathlib import Path

from .errors import TimelineCompilerError


def _sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


class AssetIndex:
    def __init__(self, manifest):
        self.requests = {item["request_id"]: item for item in manifest["requests"]}
        self.assets = {item["asset_id"]: item for item in manifest["assets"]}
        project_root = Path(manifest["library"]["project_root"])
        self.project_root = project_root if project_root.is_absolute() else project_root.absolute()

    def request(self, request_id, origin_module):
        item = self.requests.get(request_id)
        if item is None or item["origin_module"] != origin_module:
            raise TimelineCompilerError(f"Missing M6 request: {request_id}")
        return item

    def resolved(self, request, expected_type=None):
        if request["status"] != "RESOLVED":
            return None
        asset = self.assets.get(request["asset_id"])
        if asset is None:
            raise TimelineCompilerError(f"Resolved request {request['request_id']} references an unknown asset")
        if expected_type is not None and (request["asset_type"] != expected_type or asset["asset_type"] != expected_type):
            raise TimelineCompilerError(f"Resolved request {request['request_id']} has an invalid asset type")
        path = Path(asset["path"])
        if asset["path_kind"] == "PROJECT_RELATIVE":
            path = self.project_root / path
        if not path.is_file():
            raise TimelineCompilerError(f"Resolved asset does not exist: {path}")
        before = path.stat()
        if before.st_size != asset["size_bytes"] or _sha256(path) != asset["sha256"]:
            raise TimelineCompilerError(f"Resolved asset changed: {path}")
        after = path.stat()
        if (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
            raise TimelineCompilerError(f"Resolved asset changed during validation: {path}")
        return asset, path


def non_materialized(manifest):
    return [{"request_id": item["request_id"], "origin_module": item["origin_module"],
             "origin_id": item["origin_id"], "status": item["status"],
             "asset_id": item["asset_id"], "reason": item["reason"]}
            for item in manifest["requests"] if item["status"] != "RESOLVED"]
