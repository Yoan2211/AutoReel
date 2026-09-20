from core.time_ranges import cut_range_to_source_ranges, source_range_to_cut_ranges


def _merge(intervals, gap_us):
    result = []
    for start, end in sorted(intervals):
        if result and start <= result[-1][1] + gap_us:
            result[-1] = (result[-1][0], max(result[-1][1], end))
        else:
            result.append((start, end))
    return result


def speech_ranges(transcript, mappings, merge_gap_us):
    ranges = []
    for segment in transcript["segments"]:
        for word in segment["words"]:
            ranges.extend(source_range_to_cut_ranges(word["start_us"], word["end_us"], mappings))
    return _merge(ranges, merge_gap_us)


def _overlaps(start, end, intervals):
    return any(start < other_end and other_start < end for other_start, other_end in intervals)


def build_level_regions(duration_us, speech, sound_plan, mappings, config):
    sfx_times = [item["cut_time_us"] for item in sound_plan["decisions"] if item["status"] != "NONE"]
    protected = [(max(0, value - config.sfx_protection_us), min(duration_us, value + config.sfx_protection_us))
                 for value in sfx_times]
    boundaries = {0, duration_us}
    for start, end in speech + protected:
        boundaries.update((start, end))
    ordered = sorted(value for value in boundaries if 0 <= value <= duration_us)
    result = []
    for start, end in zip(ordered, ordered[1:]):
        if start == end:
            continue
        if _overlaps(start, end, speech):
            mode, gain, reason = "SPEECH_DUCK", config.speech_gain_db, "Voice present; music remains below speech"
        elif _overlaps(start, end, protected):
            mode, gain, reason = "SFX_PROTECTED", config.speech_gain_db, "Music lift blocked around an active SFX"
        else:
            containing_gap = next(((left, right) for left, right in _complement(duration_us, speech)
                                   if left <= start and end <= right), (start, end))
            if containing_gap[1] - containing_gap[0] >= config.minimum_lift_duration_us:
                mode, gain, reason = "NO_SPEECH_LIFT", config.no_speech_gain_db, "Long speech-free interval permits a restrained lift"
            else:
                mode, gain, reason = "STABLE_BASE", config.speech_gain_db, "Short pause; keep music stable instead of pumping"
        if result and result[-1]["mode"] == mode and result[-1]["gain_db"] == gain and result[-1]["cut_end_us"] == start:
            result[-1]["cut_end_us"] = end
            result[-1]["source_intervals"] = cut_range_to_source_ranges(result[-1]["cut_start_us"], end, mappings)
        else:
            result.append({"cut_start_us": start, "cut_end_us": end,
                           "source_intervals": cut_range_to_source_ranges(start, end, mappings),
                           "mode": mode, "gain_db": gain, "reason": reason})
    return result


def _complement(duration_us, intervals):
    result = []
    cursor = 0
    for start, end in intervals:
        if cursor < start:
            result.append((cursor, start))
        cursor = max(cursor, end)
    if cursor < duration_us:
        result.append((cursor, duration_us))
    return result
