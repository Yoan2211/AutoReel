import hashlib

from .errors import AssetManagerError
from .model import ValidatedAsset


PREFIX = {"IMAGE": "img", "ILLUSTRATION": "ill", "BROLL": "broll",
          "GRAPHIC": "gfx", "SFX": "sfx", "MUSIC": "music"}


def validate_candidate(candidate, probe):
    path = candidate.path
    before = path.stat()
    if before.st_size <= 0:
        raise AssetManagerError("Asset file is empty")
    metadata = probe.probe(path, candidate.asset_type)
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    after = path.stat()
    if (before.st_size, before.st_mtime_ns, before.st_ino) != (after.st_size, after.st_mtime_ns, after.st_ino):
        raise AssetManagerError("Asset changed during validation")
    return ValidatedAsset(path, candidate.asset_type, digest.hexdigest(), after.st_size, metadata)


def asset_id(asset):
    return f"{PREFIX[asset.asset_type]}_{asset.sha256[:16]}"
