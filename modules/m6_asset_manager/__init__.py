"""M6 Asset Manager public API."""

from .config import AssetManagerConfig
from .manager import resolve_assets

__all__ = ["AssetManagerConfig", "resolve_assets"]
__version__ = "1.0.0"
