"""Shared exact interval mapping between SOURCE and CUT domains."""


def source_range_to_cut_ranges(source_start_us, source_end_us, mappings):
    if type(source_start_us) is not int or type(source_end_us) is not int or source_start_us > source_end_us:
        raise ValueError("Invalid SOURCE interval")
    result = []
    for item in mappings:
        source, target = item["source"], item["target"]
        start = max(source_start_us, source["start_us"])
        end = min(source_end_us, source["end_us"])
        if start < end:
            cut_start = target["start_us"] + start - source["start_us"]
            result.append((cut_start, cut_start + end - start))
    return result


def cut_range_to_source_ranges(cut_start_us, cut_end_us, mappings):
    if type(cut_start_us) is not int or type(cut_end_us) is not int or cut_start_us > cut_end_us:
        raise ValueError("Invalid CUT interval")
    result = []
    for item in mappings:
        source, target = item["source"], item["target"]
        start = max(cut_start_us, target["start_us"])
        end = min(cut_end_us, target["end_us"])
        if start < end:
            source_start = source["start_us"] + start - target["start_us"]
            result.append({"source_start_us": source_start,
                           "source_end_us": source_start + end - start})
    return result
