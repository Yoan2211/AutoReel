"""Publish the two M2 JSON artifacts as one recoverable operation."""

import json
import os
from pathlib import Path


def _serialize(value: dict) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n"


def write_outputs(cuts_path: Path, time_map_path: Path, cuts: dict, time_map: dict) -> None:
    if cuts_path == time_map_path:
        raise ValueError("cuts and time_map destinations must differ")
    for path in (cuts_path, time_map_path):
        if path.exists() or path.is_symlink():
            raise FileExistsError(f"Output already exists: {path}")
    created: list[Path] = []
    try:
        for path, value in ((cuts_path, cuts), (time_map_path, time_map)):
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("x", encoding="utf-8", newline="\n") as output:
                created.append(path)
                output.write(_serialize(value))
                output.flush()
                os.fsync(output.fileno())
    except BaseException:
        for path in created:
            path.unlink(missing_ok=True)
        raise
