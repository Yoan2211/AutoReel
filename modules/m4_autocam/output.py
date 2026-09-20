import json, os


def write(path, value):
    if path.exists() or path.is_symlink(): raise FileExistsError(f"Camera plan exists: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with path.open("x", encoding="utf-8", newline="\n") as output:
            output.write(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False)+"\n")
            output.flush(); os.fsync(output.fileno())
    except BaseException:
        path.unlink(missing_ok=True); raise
