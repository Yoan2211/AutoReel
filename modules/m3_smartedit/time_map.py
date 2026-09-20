"""Apply M3 SOURCE removals to already-kept M2 SOURCE intervals."""

from .errors import SmartEditError


def rebuild(mappings: list[dict], removals: list[tuple[int, int]]) -> tuple[list[dict], int]:
    result, cut_cursor = [], 0
    ordered = sorted(removals)
    for remove_start, remove_end in ordered:
        if remove_start >= remove_end:
            raise SmartEditError("SmartEdit removal is empty or reversed")
    for mapping in mappings:
        start, end = mapping["source"]["start_us"], mapping["source"]["end_us"]
        fragments = [(start, end)]
        for remove_start, remove_end in ordered:
            next_fragments = []
            for fragment_start, fragment_end in fragments:
                if remove_end <= fragment_start or remove_start >= fragment_end:
                    next_fragments.append((fragment_start, fragment_end))
                else:
                    if fragment_start < remove_start:
                        next_fragments.append((fragment_start, remove_start))
                    if remove_end < fragment_end:
                        next_fragments.append((remove_end, fragment_end))
            fragments = next_fragments
        for fragment_start, fragment_end in fragments:
            duration = fragment_end - fragment_start
            if duration <= 0:
                continue
            result.append({"id": f"map{len(result):06d}",
                           "source": {"time_domain": "SOURCE", "start_us": fragment_start,
                                      "end_us": fragment_end},
                           "target": {"time_domain": "CUT", "start_us": cut_cursor,
                                      "end_us": cut_cursor + duration}})
            cut_cursor += duration
    return result, cut_cursor
