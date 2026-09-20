"""Exclusive JSON output on ordinary filesystems; never reuse M0 internals."""

import json
import os
from pathlib import Path


def write_transcript(destination: Path, transcript: dict) -> None:
    serialized = json.dumps(transcript, ensure_ascii=False, indent=2, allow_nan=False) + "\n"
    destination.parent.mkdir(parents=True, exist_ok=True)
    # Only clean a file we successfully created. Never delete a concurrent writer's file.
    with destination.open("x", encoding="utf-8", newline="\n") as output:
        try:
            output.write(serialized)
            output.flush()
            os.fsync(output.fileno())
        except BaseException:
            output.close()
            destination.unlink(missing_ok=True)
            raise
