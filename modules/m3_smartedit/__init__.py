"""M3 public API."""

from .config import SmartEditConfig
from .errors import SmartEditError
from .smartedit import smartedit

__all__ = ["SmartEditConfig", "SmartEditError", "smartedit"]
__version__ = "1.0.0"
