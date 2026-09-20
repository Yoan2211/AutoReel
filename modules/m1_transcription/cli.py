"""Standalone M1 CLI."""

import argparse
import sys

from .config import TranscriptionConfig
from .transcribe import transcribe


def main() -> int:
    parser = argparse.ArgumentParser(description="Transcribe original media from an M0 manifest")
    parser.add_argument("manifest")
    parser.add_argument("output")
    parser.add_argument("--model", default="small")
    parser.add_argument("--models-dir", default="models/faster-whisper")
    parser.add_argument("--language")
    parser.add_argument("--audio-stream-index", type=int)
    parser.add_argument("--device", choices=("cpu", "cuda", "auto"), default="cpu")
    parser.add_argument("--no-cpu-fallback", action="store_true")
    parser.add_argument("--allow-model-download", action="store_true")
    parser.add_argument("--beam-size", type=int, default=5)
    parser.add_argument("--cpu-threads", type=int, default=4)
    parser.add_argument("--ffmpeg", default="ffmpeg")
    parser.add_argument("--decode-timeout-s", type=int, default=600)
    args = parser.parse_args()
    settings = vars(args).copy()
    manifest, output = settings.pop("manifest"), settings.pop("output")
    settings["cpu_fallback"] = not settings.pop("no_cpu_fallback")
    try:
        result = transcribe(manifest, output, TranscriptionConfig(**settings))
    except (OSError, ValueError) as exc:
        print(f"M1: {exc}", file=sys.stderr)
        return 1
    print(f"M1: {output} ({len(result['segments'])} segments)")
    for warning in result["warnings"]:
        print(f"Warning: {warning}", file=sys.stderr)
    return 0
