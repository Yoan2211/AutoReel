"""M4 public API."""

from .autocam import autocam
from .config import AutoCamConfig
from .errors import AutoCamError

__all__ = ["AutoCamConfig", "AutoCamError", "autocam"]
__version__ = "1.0.0"
