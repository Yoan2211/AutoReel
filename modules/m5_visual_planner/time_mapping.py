from .errors import VisualPlannerError


def validate_mappings(mappings, output_duration_us):
    source_end = None
    cut_cursor = 0
    for item in mappings:
        source, target = item["source"], item["target"]
        if source["start_us"] >= source["end_us"] or target["start_us"] >= target["end_us"]:
            raise VisualPlannerError("Time map contains an empty or reversed interval")
        if source_end is not None and source["start_us"] < source_end:
            raise VisualPlannerError("Time map SOURCE intervals overlap or are unordered")
        if target["start_us"] != cut_cursor:
            raise VisualPlannerError("Time map CUT intervals are not contiguous")
        if source["end_us"] - source["start_us"] != target["end_us"] - target["start_us"]:
            raise VisualPlannerError("Time map changes speed")
        source_end, cut_cursor = source["end_us"], target["end_us"]
    if cut_cursor != output_duration_us:
        raise VisualPlannerError("Time map duration disagrees with mappings")


def best_retained_window(source_start_us, source_end_us, mappings):
    overlaps = []
    for item in mappings:
        source, target = item["source"], item["target"]
        start = max(source_start_us, source["start_us"])
        end = min(source_end_us, source["end_us"])
        if start < end:
            cut_start = target["start_us"] + start - source["start_us"]
            overlaps.append((start, end, cut_start, cut_start + end - start))
    return max(overlaps, key=lambda item: (item[1] - item[0], -item[0])) if overlaps else None
