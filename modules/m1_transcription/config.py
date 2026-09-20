"""M1 configuration, independent of every other module."""

from dataclasses import dataclass
import re


@dataclass(frozen=True)
class TranscriptionConfig:
    model: str = "small"
    models_dir: str = "models/faster-whisper"
    language: str | None = None
    audio_stream_index: int | None = None
    device: str = "cpu"
    cpu_fallback: bool = True
    allow_model_download: bool = False
    beam_size: int = 5
    cpu_threads: int = 4
    ffmpeg: str = "ffmpeg"
    decode_timeout_s: int = 600

    def __post_init__(self) -> None:
        for name in ("model", "models_dir", "ffmpeg"):
            if not isinstance(getattr(self, name), str) or not getattr(self, name).strip():
                raise ValueError(f"{name} must be a non-empty string")
        for name in ("beam_size", "cpu_threads", "decode_timeout_s"):
            if type(getattr(self, name)) is not int or getattr(self, name) <= 0:
                raise ValueError(f"{name} must be a positive integer")
        if self.device not in ("cpu", "cuda", "auto"):
            raise ValueError("device must be cpu, cuda or auto")
        if type(self.cpu_fallback) is not bool or type(self.allow_model_download) is not bool:
            raise ValueError("Fallback and download options must be booleans")
        if self.audio_stream_index is not None and (
            type(self.audio_stream_index) is not int or self.audio_stream_index < 0
        ):
            raise ValueError("audio_stream_index must be a non-negative integer")
        if self.language is not None and (
            not isinstance(self.language, str) or not re.fullmatch("[a-z]{2,3}", self.language)
        ):
            raise ValueError("language must be a lowercase language code, e.g. fr")
