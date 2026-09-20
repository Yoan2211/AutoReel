"""Build the explicit SOURCE to CUT map from accepted removals."""

from .errors import SpeechCutError
from .model import Candidate


def build_time_map(source_start_us: int, source_end_us: int,
                   removals: list[Candidate]) -> tuple[list[dict], int]:
    if source_start_us > source_end_us:
        raise SpeechCutError("Invalid analysis bounds")
    mappings = []
    cursor = source_start_us
    cut_cursor = 0
    for removal in removals:
        start = max(source_start_us, removal.start_us)
        end = min(source_end_us, removal.end_us)
        if start < cursor or end < start:
            raise SpeechCutError("Applied removals overlap or are invalid")
        if cursor < start:
            duration = start - cursor
            mappings.append({
                "id": f"map{len(mappings):06d}",
                "source": {"time_domain": "SOURCE", "start_us": cursor, "end_us": start},
                "target": {"time_domain": "CUT", "start_us": cut_cursor, "end_us": cut_cursor + duration},
            })
            cut_cursor += duration
        cursor = end
    if cursor < source_end_us:
        duration = source_end_us - cursor
        mappings.append({
            "id": f"map{len(mappings):06d}",
            "source": {"time_domain": "SOURCE", "start_us": cursor, "end_us": source_end_us},
            "target": {"time_domain": "CUT", "start_us": cut_cursor, "end_us": cut_cursor + duration},
        })
        cut_cursor += duration
    return mappings, cut_cursor
