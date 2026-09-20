"""Publish complete JSON exclusively, without replacing an existing manifest."""

import os
from pathlib import Path
import tempfile


def publish_manifest(destination: Path, serialized: str) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    # A sibling staging file makes publication atomic on supported filesystems.
    fd, name = tempfile.mkstemp(prefix=".m0-", suffix=".tmp", dir=destination.parent)
    staged = Path(name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as output:
            output.write(serialized)
            output.flush()
            os.fsync(output.fileno())
        # Unlike replace(), link() fails if a destination was concurrently created.
        # NTFS supports hard links; unsupported filesystems fail without publication.
        os.link(staged, destination)
    finally:
        staged.unlink(missing_ok=True)

