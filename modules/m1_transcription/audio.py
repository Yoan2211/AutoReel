"""Decode a selected source stream to a disposable, time-aligned PCM waveform."""

from dataclasses import dataclass
from pathlib import Path
import subprocess
import wave

from core.time import ticks_to_us, us_to_seconds_text
from .config import TranscriptionConfig
from .errors import TranscriptionError


@dataclass(frozen=True)
class AnalysisAudio:
    path: Path
    origin_us: int
    duration_us: int


def extract_audio(source: Path, stream: dict, destination: Path,
                  config: TranscriptionConfig) -> AnalysisAudio:
    origin = stream["start_us"]
    # Keep absolute input PTS, translate to the declared audio origin, then fill
    # timestamp gaps with silence. No VAD, silence removal or montage here.
    filters = (
        f"asetpts=PTS-({us_to_seconds_text(origin)})/TB,"
        "aresample=16000:async=1:first_pts=0:min_hard_comp=0.0000625"
    )
    command = [
        config.ffmpeg, "-nostdin", "-hide_banner", "-loglevel", "error", "-n",
        "-copyts", "-i", str(source), "-map", f"0:{stream['stream_index']}",
        "-vn", "-sn", "-dn", "-af", filters, "-ac", "1", "-ar", "16000",
        "-c:a", "pcm_s16le", "-map_metadata", "-1", str(destination),
    ]
    try:
        result = subprocess.run(command, capture_output=True, text=True, encoding="utf-8",
                                errors="replace", timeout=config.decode_timeout_s, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise TranscriptionError(f"FFmpeg unavailable or decode timed out: {exc}") from exc
    if result.returncode:
        raise TranscriptionError(f"FFmpeg audio decode failed: {result.stderr.strip()[:1000]}")
    try:
        with wave.open(str(destination), "rb") as audio:
            if (audio.getnchannels(), audio.getsampwidth(), audio.getframerate()) != (1, 2, 16000):
                raise TranscriptionError("Unexpected analysis audio format")
            duration = ticks_to_us(audio.getnframes(), "1/16000")
    except (OSError, wave.Error, EOFError) as exc:
        raise TranscriptionError(f"Invalid analysis WAV: {exc}") from exc
    if duration <= 0:
        raise TranscriptionError("Decoded audio is empty")
    return AnalysisAudio(destination, origin, duration)


def is_digital_silence(path: Path) -> bool:
    """True only for non-empty PCM16 audio with every sample exactly zero."""
    try:
        with wave.open(str(path), "rb") as audio:
            if audio.getsampwidth() != 2 or audio.getcomptype() != "NONE":
                raise TranscriptionError("Silence check requires uncompressed PCM16")
            if audio.getnframes() == 0:
                return False
            while chunk := audio.readframes(65536):
                if any(chunk):
                    return False
            return True
    except (OSError, wave.Error, EOFError) as exc:
        raise TranscriptionError(f"Cannot inspect analysis audio: {exc}") from exc
