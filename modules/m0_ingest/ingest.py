"""M0 orchestration: original media → source manifest, never re-encode."""

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

from .metadata import normalize
from .manifest import publish_manifest
from .probe import IngestError, probe_media


@dataclass(frozen=True)
class IngestConfig:
    ffprobe: str = "ffprobe"
    timeout_s: int = 60

    def __post_init__(self) -> None:
        if not self.ffprobe or not isinstance(self.ffprobe, str):
            raise ValueError("ffprobe must be a non-empty executable path")
        if type(self.timeout_s) is not int or self.timeout_s <= 0:
            raise ValueError("timeout_s must be a positive integer")


def ingest(source: str | Path, manifest_path: str | Path,
           config: IngestConfig | None = None) -> dict:
    config = config or IngestConfig()
    source = Path(source).resolve(strict=True)
    destination = Path(manifest_path).absolute()
    if destination.exists():
        raise FileExistsError(f"Manifest already exists: {destination}")
    if not source.is_file() or source.suffix.lower() not in (".mp4", ".mov"):
        raise IngestError("Source must be an existing MP4/MOV file")
    before = source.stat()
    if before.st_size == 0:
        raise IngestError("Empty source file")
    metadata, warnings = normalize(probe_media(source, config.ffprobe, config.timeout_s))
    digest = hashlib.sha256()
    with source.open("rb") as media:
        for block in iter(lambda: media.read(1024 * 1024), b""):
            digest.update(block)
    after = source.stat()
    if (before.st_size, before.st_mtime_ns, before.st_ino) != (after.st_size, after.st_mtime_ns, after.st_ino):
        raise IngestError("Source changed during ingest; retry when recording/copying is complete")
    result = {
        "schema_version": "1.0.0", "module": {"id": "M0", "version": "1.0.0"},
        "source": {"path": str(source), "size_bytes": after.st_size,
                   "sha256": digest.hexdigest(), **metadata},
        "warnings": warnings,
    }
    serialized = json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False) + "\n"
    publish_manifest(destination, serialized)
    return result

