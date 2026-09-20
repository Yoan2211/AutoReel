"""Shared integer mapping between SOURCE and CUT domains."""


def validate_source_cut_map(mappings, output_duration_us, error_type=ValueError):
    source_cursor = None
    cut_cursor = 0
    for item in mappings:
        source, target = item["source"], item["target"]
        if source["start_us"] >= source["end_us"] or target["start_us"] >= target["end_us"]:
            raise error_type("Time map contains an empty or reversed interval")
        if source_cursor is not None and source["start_us"] < source_cursor:
            raise error_type("Time map SOURCE intervals overlap or are unordered")
        if target["start_us"] != cut_cursor:
            raise error_type("Time map CUT intervals are not contiguous")
        if source["end_us"] - source["start_us"] != target["end_us"] - target["start_us"]:
            raise error_type("Time map changes speed")
        source_cursor, cut_cursor = source["end_us"], target["end_us"]
    if cut_cursor != output_duration_us:
        raise error_type("Time map duration disagrees with mappings")


def source_to_cut_us(source_us, mappings):
    if type(source_us) is not int:
        raise ValueError("SOURCE timestamp must be integer microseconds")
    for item in mappings:
        source, target = item["source"], item["target"]
        if source["start_us"] <= source_us < source["end_us"]:
            return target["start_us"] + source_us - source["start_us"]
    return None
