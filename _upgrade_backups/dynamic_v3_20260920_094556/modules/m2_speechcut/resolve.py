"""Resolve overlapping proposals without hiding discarded evidence."""

from .model import Candidate


PRIORITY = {"IMMEDIATE_REPETITION": 30, "FILLER": 20, "LONG_SILENCE": 10}


def select_auto(candidates: list[Candidate]) -> tuple[list[Candidate], set[int]]:
    indexed = [(index, item) for index, item in enumerate(candidates) if item.disposition == "AUTO"]
    indexed.sort(key=lambda pair: (-PRIORITY[pair[1].kind], pair[1].start_us, pair[1].end_us))
    selected: list[tuple[int, Candidate]] = []
    suppressed: set[int] = set()
    for index, candidate in indexed:
        if any(candidate.start_us < other.end_us and other.start_us < candidate.end_us for _, other in selected):
            suppressed.add(index)
        else:
            selected.append((index, candidate))
    selected.sort(key=lambda pair: pair[1].start_us)
    return [item for _, item in selected], suppressed
