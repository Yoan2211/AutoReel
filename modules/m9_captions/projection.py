from dataclasses import dataclass

from .errors import CaptionsError


@dataclass(frozen=True)
class ProjectedWord:
    id: str
    segment_id: str
    text: str
    source_start_us: int
    source_end_us: int
    cut_start_us: int
    cut_end_us: int
    timeline_start_us: int
    timeline_end_us: int


def validate_v1(events, duration_us):
    cursor = 0
    previous_source_end = None
    for event in events:
        values = (event["source_start_us"], event["source_end_us"], event["cut_start_us"],
                  event["cut_end_us"], event["timeline_start_us"], event["timeline_end_us"])
        if any(type(value) is not int for value in values):
            raise CaptionsError("V1 timestamps must be integer microseconds")
        source_start, source_end, cut_start, cut_end, timeline_start, timeline_end = values
        if source_start >= source_end or cut_start >= cut_end or timeline_start >= timeline_end:
            raise CaptionsError("V1 contains a duration <= 0")
        if source_end - source_start != cut_end - cut_start or cut_end - cut_start != timeline_end - timeline_start:
            raise CaptionsError("V1 mapping changes speed")
        if cut_start != cursor or timeline_start != cursor or cut_start != timeline_start or cut_end != timeline_end:
            raise CaptionsError("V1 CUT/TIMELINE mapping is not contiguous Pass A chronology")
        if previous_source_end is not None and source_start < previous_source_end:
            raise CaptionsError("V1 SOURCE intervals overlap or are unordered")
        cursor, previous_source_end = cut_end, source_end
    if cursor != duration_us:
        raise CaptionsError("V1 duration disagrees with timeline format")


def project_words(transcript, v1_events):
    result = []
    for segment in transcript["segments"]:
        for word in segment["words"]:
            if word["start_us"] >= word["end_us"]:
                continue
            event = next((item for item in v1_events
                          if item["source_start_us"] <= word["start_us"] and
                          word["end_us"] <= item["source_end_us"]), None)
            if event is None:
                continue
            source_offset = word["start_us"] - event["source_start_us"]
            duration = word["end_us"] - word["start_us"]
            result.append(ProjectedWord(
                word["id"], segment["id"], word["text"], word["start_us"], word["end_us"],
                event["cut_start_us"] + source_offset, event["cut_start_us"] + source_offset + duration,
                event["timeline_start_us"] + source_offset,
                event["timeline_start_us"] + source_offset + duration))
    result.sort(key=lambda item: (item.timeline_start_us, item.timeline_end_us, item.id))
    if any(left.timeline_end_us > right.timeline_start_us for left, right in zip(result, result[1:])):
        raise CaptionsError("Projected word timings overlap")
    return result


def source_intervals_for_range(start_us, end_us, events):
    result = []
    for event in events:
        start = max(start_us, event["timeline_start_us"])
        end = min(end_us, event["timeline_end_us"])
        if start < end:
            source_start = event["source_start_us"] + start - event["timeline_start_us"]
            result.append({"source_start_us": source_start,
                           "source_end_us": source_start + end - start})
    return result
