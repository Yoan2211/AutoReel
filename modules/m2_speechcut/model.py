"""M2-internal immutable values. Public interchange remains JSON."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Word:
    id: str
    start_us: int
    end_us: int
    text: str
    token: str
    segment_id: str

    @property
    def duration_us(self) -> int:
        return self.end_us - self.start_us


@dataclass(frozen=True)
class Candidate:
    kind: str
    start_us: int
    end_us: int
    disposition: str
    confidence: str
    reason: str
    word_ids: tuple[str, ...] = ()
    retained_pause_us: int | None = None

    @property
    def duration_us(self) -> int:
        return self.end_us - self.start_us
