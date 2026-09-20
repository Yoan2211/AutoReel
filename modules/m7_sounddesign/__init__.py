"""M7 SoundDesign public API."""

from .config import SoundDesignConfig
from .planner import plan_sounds

__all__ = ["SoundDesignConfig", "plan_sounds"]
__version__ = "1.0.0"
