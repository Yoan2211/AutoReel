from pathlib import Path
from typing import Iterable, Protocol

from .model import Detection, Frame


class FrameProvider(Protocol):
    def frames(self, source: Path, intervals: list[tuple[int, int]], source_origin_us: int,
               rotation_degrees: int, sample_interval_us: int) -> Iterable[Frame]: ...


class SubjectDetector(Protocol):
    name: str
    version: str
    device: str
    def detect(self, frame: Frame) -> list[Detection]: ...
