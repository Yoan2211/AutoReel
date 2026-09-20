from .contracts import validate
from .errors import TimelineCompilerError
from .validation import TRACKS


def _source_intervals(start, end, v1_events):
    result = []
    for event in v1_events:
        overlap_start = max(start, event["timeline_start_us"])
        overlap_end = min(end, event["timeline_end_us"])
        if overlap_start < overlap_end:
            source_start = event["source_start_us"] + overlap_start - event["timeline_start_us"]
            result.append({"source_start_us": source_start,
                           "source_end_us": source_start + overlap_end - overlap_start})
    return result


def validate_caption_inputs(captions, duration_us, v1_events):
    previous_end = None
    for caption in captions["captions"]:
        start, end = caption["timeline_start_us"], caption["timeline_end_us"]
        if start < 0 or start >= end or end > duration_us:
            raise TimelineCompilerError(f"Caption {caption['id']} is outside timeline duration")
        if previous_end is not None and start < previous_end:
            raise TimelineCompilerError("Captions overlap")
        previous_end = end
        if (caption["cut_start_us"], caption["cut_end_us"]) != (start, end):
            raise TimelineCompilerError(f"Caption {caption['id']} has inconsistent CUT/TIMELINE timestamps")
        intervals = caption["source_intervals"]
        if not intervals or any(item["source_start_us"] >= item["source_end_us"] for item in intervals):
            raise TimelineCompilerError(f"Caption {caption['id']} has invalid SOURCE intervals")
        if intervals != _source_intervals(start, end, v1_events):
            raise TimelineCompilerError(f"Caption {caption['id']} SOURCE intervals disagree with V1")
        if caption["source_start_us"] != intervals[0]["source_start_us"] or caption["source_end_us"] != intervals[-1]["source_end_us"]:
            raise TimelineCompilerError(f"Caption {caption['id']} has inconsistent SOURCE bounds")
        words = caption["words"]
        if not words or caption["word_ids"] != [word["id"] for word in words]:
            raise TimelineCompilerError(f"Caption {caption['id']} has invalid words")
        if caption["text"] != "".join(word["text"] for word in words).strip():
            raise TimelineCompilerError(f"Caption {caption['id']} text differs from its spoken words")
        for word in words:
            if word["cut_start_us"] != word["timeline_start_us"] or word["cut_end_us"] != word["timeline_end_us"]:
                raise TimelineCompilerError(f"Caption {caption['id']} word has inconsistent CUT/TIMELINE timestamps")
            if not start <= word["timeline_start_us"] < word["timeline_end_us"] <= end:
                raise TimelineCompilerError(f"Caption {caption['id']} word is outside its caption")
            matching = next((event for event in v1_events
                             if event["timeline_start_us"] <= word["timeline_start_us"] and
                             word["timeline_end_us"] <= event["timeline_end_us"]), None)
            if matching is None:
                raise TimelineCompilerError(f"Caption {caption['id']} word is outside V1")
            source_start = matching["source_start_us"] + word["timeline_start_us"] - matching["timeline_start_us"]
            if (word["source_start_us"], word["source_end_us"]) != (
                    source_start, source_start + word["timeline_end_us"] - word["timeline_start_us"]):
                raise TimelineCompilerError(f"Caption {caption['id']} word SOURCE timing disagrees with V1")


def validate_final(value, draft, captions):
    validate(value, "timeline-1.0.0.json")
    expected_layout = [(item[0], item[1], item[2], item[3]) for item in TRACKS]
    actual_layout = [(item["id"], item["kind"], item["index"], item["role"]) for item in value["tracks"]]
    if actual_layout != expected_layout:
        raise TimelineCompilerError("Final timeline has an invalid track layout")
    draft_tracks = {item["id"]: item for item in draft["tracks"]}
    final_tracks = {item["id"]: item for item in value["tracks"]}
    if draft_tracks["V3"]["events"]:
        raise TimelineCompilerError("Pass A V3 is not reserved and empty")
    for track_id in ("V1", "V2", "A1", "A2", "A3"):
        if final_tracks[track_id] != draft_tracks[track_id]:
            raise TimelineCompilerError(f"Final compilation changed Pass A track {track_id}")
    if value["unmaterialized"] != draft["unmaterialized"] or value["diagnostics"] != draft["diagnostics"]:
        raise TimelineCompilerError("Final compilation changed Pass A diagnostics")
    if len(final_tracks["V3"]["events"]) != len(captions["captions"]):
        raise TimelineCompilerError("Final V3 caption count disagrees with M9")
