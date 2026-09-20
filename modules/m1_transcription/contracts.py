"""Read and validate JSON contracts; verify the original source identity."""

import hashlib
from importlib.resources import files
import json
from pathlib import Path

from .errors import TranscriptionError


def _reject_constant(value: str):
    raise TranscriptionError(f"Non-finite JSON value: {value}")


def validate_contract(data: dict, schema_name: str) -> None:
    try:
        from jsonschema import Draft202012Validator
    except ImportError as exc:
        raise TranscriptionError('Install M1 dependencies: pip install -e ".[transcription]"') from exc
    schema = json.loads(files("core").joinpath("schemas", schema_name).read_text(encoding="utf-8-sig"))
    error = next(Draft202012Validator(schema).iter_errors(data), None)
    if error:
        raise TranscriptionError(f"Invalid {schema_name} at {list(error.path)}: {error.message}")


def load_source(manifest: Path, stream_index: int | None) -> tuple[dict, dict, str]:
    raw = manifest.read_bytes()
    try:
        data = json.loads(raw.decode("utf-8-sig"), parse_constant=_reject_constant)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise TranscriptionError("Invalid source manifest JSON") from exc
    validate_contract(data, "source-manifest-1.0.0.json")
    source = data["source"]
    if not Path(source["path"]).is_absolute():
        raise TranscriptionError("Source path must be absolute")
    audio = source["audio"]
    if not audio:
        raise TranscriptionError("Source has no audio stream to transcribe")
    indices = [s["stream_index"] for s in audio] + [source["video"]["stream_index"]]
    if len(set(indices)) != len(indices):
        raise TranscriptionError("Source stream indices must be unique")
    if stream_index is None:
        if len(audio) != 1:
            raise TranscriptionError("Multiple audio streams: specify audio_stream_index")
        selected = audio[0]
    else:
        selected = next((s for s in audio if s["stream_index"] == stream_index), None)
        if selected is None:
            raise TranscriptionError(f"Audio stream {stream_index} is not in the source manifest")
    return source, selected, hashlib.sha256(raw).hexdigest()


def source_signature(path: Path) -> tuple[int, int, int]:
    stat = path.stat()
    return stat.st_size, stat.st_mtime_ns, stat.st_ino


def verify_source(source: dict) -> tuple[int, int, int]:
    path = Path(source["path"])
    if not path.is_file():
        raise TranscriptionError("Original source is not a regular file")
    before = source_signature(path)
    if before[0] != source["size_bytes"]:
        raise TranscriptionError("Original source size no longer matches M0")
    digest = hashlib.sha256()
    with path.open("rb") as media:
        for block in iter(lambda: media.read(1024 * 1024), b""):
            digest.update(block)
    if before != source_signature(path) or digest.hexdigest() != source["sha256"]:
        raise TranscriptionError("Original source identity no longer matches M0")
    return before
