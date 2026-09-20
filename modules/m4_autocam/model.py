from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class Frame:
    source_us: int
    image: Any
    width: int
    height: int


@dataclass(frozen=True)
class Detection:
    kind: str
    x: float
    y: float
    width: float
    height: float
    confidence: float

    @property
    def center(self): return self.x + self.width / 2, self.y + self.height / 2


@dataclass
class Track:
    id: int
    detection: Detection
    last_seen_us: int
    missed: int = 0
