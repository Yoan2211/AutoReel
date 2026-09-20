import json
import re
import unicodedata

from .model import Candidate


EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".mp4", ".mov", ".mkv", ".webm",
              ".wav", ".mp3", ".flac", ".m4a", ".aac", ".ogg"}
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}
VIDEO_EXTENSIONS = {".mp4", ".mov", ".mkv", ".webm"}
AUDIO_EXTENSIONS = {".wav", ".mp3", ".flac", ".m4a", ".aac", ".ogg"}


def tokenize(value):
    normalized = unicodedata.normalize("NFC", value.casefold()).replace("_", " ").replace("-", " ")
    return tuple(re.findall(r"[\w'-]+", normalized, re.UNICODE))


def _inferred_type(path):
    parts = {part.casefold() for part in path.parts}
    suffix = path.suffix.casefold()
    if suffix in VIDEO_EXTENSIONS:
        return "BROLL"
    if suffix in AUDIO_EXTENSIONS:
        return "MUSIC" if parts & {"music", "musique", "songs", "tracks"} else "SFX"
    if parts & {"illustration", "illustrations"}:
        return "ILLUSTRATION"
    if parts & {"icon", "icons", "graphic", "graphics", "graphiques"}:
        return "GRAPHIC"
    return "IMAGE"


def scan(root, recursive=True):
    iterator = root.rglob("*") if recursive else root.glob("*")
    candidates, issues = [], []
    for path in sorted((item for item in iterator if item.is_file() and item.suffix.casefold() in EXTENSIONS),
                       key=lambda item: item.as_posix().casefold()):
        sidecar = path.with_suffix(path.suffix + ".asset.json")
        data = {}
        if sidecar.exists():
            try:
                data = json.loads(sidecar.read_text(encoding="utf-8-sig"))
                if not isinstance(data, dict) or not isinstance(data.get("tags", []), list):
                    raise ValueError("sidecar must be an object with an optional tags array")
            except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
                issues.append({"path": str(sidecar), "reason": f"Invalid sidecar: {exc}"})
                continue
        asset_type = data.get("asset_type", _inferred_type(path))
        if asset_type not in {"IMAGE", "ILLUSTRATION", "BROLL", "GRAPHIC", "SFX", "MUSIC"}:
            issues.append({"path": str(sidecar), "reason": "Invalid asset_type in sidecar"})
            continue
        tags = tuple(str(item) for item in data.get("tags", []))
        relative_words = " ".join(path.relative_to(root).with_suffix("").parts)
        candidates.append(Candidate(path, asset_type, tags, tokenize(relative_words + " " + " ".join(tags))))
    return candidates, issues
