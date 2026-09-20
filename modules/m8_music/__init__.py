"""M8 Music Planner public API."""

from .config import MusicPlannerConfig
from .planner import plan_music

__all__ = ["MusicPlannerConfig", "plan_music"]
__version__ = "1.0.0"
