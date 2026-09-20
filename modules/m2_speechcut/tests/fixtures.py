"""M1-contract fixtures built without importing M1 implementation."""

import hashlib
import json
from pathlib import Path


def word(index: int, text: str, start_us: int, end_us: int, segment: int = 0) -> dict:
    return {
        "id": f"s{segment:06d}w{index:06d}", "start_us": start_us,
        "end_us": end_us, "text": text, "probability": 0.95,
    }


def transcript(words: list[dict], *, origin_us: int = 0,
               duration_us: int = 10_000_000, segments: list[dict] | None = None) -> dict:
    if segments is None:
        text = "".join(item["text"] for item in words)
        segments = [{
            "id": "s000000", "start_us": words[0]["start_us"] if words else origin_us,
            "end_us": words[-1]["end_us"] if words else origin_us,
            "text": text, "no_speech_probability": 0.01, "words": words,
        }] if words else []
    return {
        "schema_version": "1.0.0", "module": {"id": "M1", "version": "1.0.0"},
        "time_domain": "SOURCE",
        "source": {"path": "C:\\media\\source.mov", "sha256": "a" * 64,
                   "manifest_sha256": "b" * 64, "audio_stream_index": 1},
        "analysis": {"origin_us": origin_us, "duration_us": duration_us,
                     "sample_rate_hz": 16000, "channels": 1},
        "engine": {"name": "fixture", "version": "1", "model": "fixture",
                   "device": "cpu", "compute_type": "int8"},
        "options": {"language_requested": "fr", "beam_size": 5,
                    "word_timestamps": True, "vad_filter": False,
                    "condition_on_previous_text": False, "task": "transcribe"},
        "language": "fr", "language_probability": 0.99,
        "status": "transcribed" if words else "no_speech_recognized",
        "text": "".join(segment["text"] for segment in segments).strip(),
        "segments": segments,
        "warnings": [] if words else ["NO_SPEECH_RECOGNIZED"],
    }


def save(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")
