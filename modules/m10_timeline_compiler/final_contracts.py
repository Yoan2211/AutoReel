import hashlib
import json
from pathlib import Path

from .contracts import validate
from .errors import TimelineCompilerError


def _read(path, schema):
    raw = path.read_bytes()
    try:
        value = json.loads(raw.decode("utf-8-sig"), parse_constant=lambda item: (_ for _ in ()).throw(
            TimelineCompilerError(f"Non-finite JSON: {item}")))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise TimelineCompilerError(f"Invalid JSON: {path}") from exc
    validate(value, schema)
    return value, hashlib.sha256(raw).hexdigest()


def _signature(path):
    stat = path.stat()
    return stat.st_size, stat.st_mtime_ns, getattr(stat, "st_ino", None)


def load_final_inputs(timeline_draft_path, captions_path):
    draft_path = Path(timeline_draft_path).resolve(strict=True)
    captions_path = Path(captions_path).resolve(strict=True)
    draft_signature, captions_signature = _signature(draft_path), _signature(captions_path)
    draft, draft_hash = _read(draft_path, "timeline-draft-1.0.0.json")
    captions, captions_hash = _read(captions_path, "captions-1.0.0.json")
    referenced = Path(captions["source"]["timeline_draft_path"]).resolve(strict=True)
    if referenced != draft_path or captions["source"]["timeline_draft_sha256"] != draft_hash:
        raise TimelineCompilerError("captions.json does not reference exactly the supplied timeline_draft.json")
    return draft, captions, draft_hash, captions_hash, draft_path, captions_path, draft_signature, captions_signature


def verify_unchanged(path, signature, expected_hash, label):
    if not path.is_file() or _signature(path) != signature:
        raise TimelineCompilerError(f"{label} disappeared or changed during final compilation")
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    if digest != expected_hash:
        raise TimelineCompilerError(f"{label} changed during final compilation")
