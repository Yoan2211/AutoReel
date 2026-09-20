"""M1 public API; heavy ASR dependencies are loaded only when used."""

from .config import TranscriptionConfig
from .errors import TranscriptionError
from .transcribe import transcribe

__all__ = ["TranscriptionConfig", "TranscriptionError", "transcribe"]
__version__ = "1.0.0"
