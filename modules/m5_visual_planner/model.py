from dataclasses import dataclass


@dataclass(frozen=True)
class Candidate:
    passage_id: str
    section_id: str
    source_start_us: int
    source_end_us: int
    cut_start_us: int
    cut_end_us: int
    concept: str
    media_type: str
    score: float
    reason: str
