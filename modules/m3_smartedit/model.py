from dataclasses import dataclass


@dataclass(frozen=True)
class Passage:
    id: str
    source_start_us: int
    source_end_us: int
    text: str
    word_ids: tuple[str, ...]
    tokens: tuple[str, ...]
    strength: float
