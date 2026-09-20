import json
import os
from pathlib import Path


def serialize(value: dict) -> bytes:
    return (json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n").encode("utf-8")


def write_outputs(plan_path: Path, map_path: Path, plan: dict, time_map: dict) -> None:
    if plan_path == map_path:
        raise ValueError("edit plan and time map destinations must differ")
    for path in (plan_path, map_path):
        if path.exists() or path.is_symlink():
            raise FileExistsError(f"Output already exists: {path}")
    created = []
    try:
        for path, value in ((plan_path, plan), (map_path, time_map)):
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("xb") as output:
                created.append(path)
                output.write(serialize(value))
                output.flush()
                os.fsync(output.fileno())
    except BaseException:
        for path in created:
            path.unlink(missing_ok=True)
        raise
