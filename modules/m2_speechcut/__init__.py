"""M2 public API."""

from .config import SpeechCutConfig
from .errors import SpeechCutError
from .speechcut import speechcut

__all__ = ["SpeechCutConfig", "SpeechCutError", "speechcut"]
__version__ = "1.0.0"
