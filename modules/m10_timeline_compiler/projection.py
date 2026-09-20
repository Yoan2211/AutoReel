from .errors import TimelineCompilerError


def timeline_range(cut_start_us, cut_end_us, timeline_offset_us=0):
    if type(cut_start_us) is not int or type(cut_end_us) is not int:
        raise TimelineCompilerError("CUT timestamps must be integer microseconds")
    if cut_start_us < 0 or cut_start_us >= cut_end_us:
        raise TimelineCompilerError("Duration must be greater than zero")
    return cut_start_us + timeline_offset_us, cut_end_us + timeline_offset_us


def project_source_range(source_start_us, source_end_us, mappings):
    if type(source_start_us) is not int or type(source_end_us) is not int or source_start_us >= source_end_us:
        raise TimelineCompilerError("Invalid SOURCE interval or duration <= 0")
    pieces = []
    for item in mappings:
        source, cut = item["source"], item["target"]
        start = max(source_start_us, source["start_us"])
        end = min(source_end_us, source["end_us"])
        if start < end:
            cut_start = cut["start_us"] + start - source["start_us"]
            pieces.append((start, end, cut_start, cut_start + end - start))
    return pieces


def project_source_point(source_us, mappings, allow_program_end=False):
    if type(source_us) is not int:
        raise TimelineCompilerError("SOURCE timestamp must be integer microseconds")
    for item in mappings:
        source, cut = item["source"], item["target"]
        if source["start_us"] <= source_us < source["end_us"]:
            return cut["start_us"] + source_us - source["start_us"]
    if allow_program_end and mappings and source_us == mappings[-1]["source"]["end_us"]:
        return mappings[-1]["target"]["end_us"]
    return None


def require_exact_projection(source_start_us, source_end_us, cut_start_us, cut_end_us, mappings, label):
    pieces = project_source_range(source_start_us, source_end_us, mappings)
    if len(pieces) != 1:
        raise TimelineCompilerError(f"{label}: event is outside retained material or crosses a removed interval")
    projected = pieces[0]
    if (projected[2], projected[3]) != (cut_start_us, cut_end_us):
        raise TimelineCompilerError(f"{label}: inconsistent SOURCE/CUT timestamps")
    return projected


def require_cut_range(cut_start_us, cut_end_us, duration_us, label):
    timeline_range(cut_start_us, cut_end_us)
    if cut_end_us > duration_us:
        raise TimelineCompilerError(f"{label}: event is outside retained material")
