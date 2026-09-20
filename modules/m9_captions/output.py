import json
import os


def write_exclusive(path, value):
    if path.exists() or path.is_symlink():
        raise FileExistsError(f"Captions output exists: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with path.open("x", encoding="utf-8", newline="\n") as stream:
            stream.write(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n")
            stream.flush(); os.fsync(stream.fileno())
    except BaseException:
        path.unlink(missing_ok=True)
        raise
