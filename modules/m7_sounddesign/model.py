from dataclasses import dataclass


@dataclass(frozen=True)
class Event:
    id: str
    kind: str
    source_time_us: int
    cut_time_us: int
    score: float
    context: str
    origin_ids: tuple[str, ...]


@dataclass(frozen=True)
class ClassifiedEvent:
    event: Event
    sound_type: str
    gain_db: float
    reason: str
