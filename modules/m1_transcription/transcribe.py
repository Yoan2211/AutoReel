"""M1 orchestration: M0 JSON + original media to SOURCE transcription JSON."""

from pathlib import Path
import tempfile

from .audio import extract_audio
from .backend import TranscriptionBackend
from .config import TranscriptionConfig
from .contracts import load_source, source_signature, validate_contract, verify_source
from .errors import TranscriptionError
from .faster_whisper_backend import FasterWhisperBackend
from .normalize import normalize
from .output import write_transcript


def transcribe(manifest_path: str | Path, output_path: str | Path,
               config: TranscriptionConfig | None = None, *,
               backend: TranscriptionBackend | None = None) -> dict:
    config = config or TranscriptionConfig()
    manifest = Path(manifest_path).resolve(strict=True)
    destination = Path(output_path).absolute()
    if destination.exists() or destination.is_symlink():
        raise FileExistsError(f"Transcript already exists: {destination}")
    source, stream, manifest_hash = load_source(manifest, config.audio_stream_index)
    signature = verify_source(source)
    with tempfile.TemporaryDirectory(prefix="autoreel-m1-") as temporary:
        audio = extract_audio(Path(source["path"]), stream, Path(temporary) / "analysis.wav", config)
        recognition = (backend or FasterWhisperBackend()).recognize(audio.path, config)
        segments, warnings = normalize(recognition, audio)
        if signature != source_signature(Path(source["path"])):
            raise TranscriptionError("Original source changed during transcription")
        result = {
            "schema_version": "1.0.0", "module": {"id": "M1", "version": "1.0.0"},
            "time_domain": "SOURCE",
            "source": {"path": source["path"], "sha256": source["sha256"],
                       "manifest_sha256": manifest_hash, "audio_stream_index": stream["stream_index"]},
            "analysis": {"origin_us": audio.origin_us, "duration_us": audio.duration_us,
                         "sample_rate_hz": 16000, "channels": 1},
            "engine": {"name": recognition.engine, "version": recognition.engine_version,
                       "model": config.model, "device": recognition.device,
                       "compute_type": recognition.compute_type},
            "options": {"language_requested": config.language, "beam_size": config.beam_size,
                        "word_timestamps": True, "vad_filter": False,
                        "condition_on_previous_text": False, "task": "transcribe"},
            "language": recognition.language, "language_probability": recognition.language_probability,
            "status": "transcribed" if segments else "no_speech_recognized",
            "text": "".join(s["text"] for s in segments).strip(),
            "segments": segments, "warnings": warnings,
        }
        validate_contract(result, "transcript-1.0.0.json")
    write_transcript(destination, result)
    return result
