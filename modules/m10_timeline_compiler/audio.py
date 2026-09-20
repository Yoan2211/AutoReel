from .errors import TimelineCompilerError
from core.time_ranges import cut_range_to_source_ranges

from .projection import project_source_point, require_cut_range


def source_audio_events(media, mappings):
    if not media["audio"]:
        return []
    if len(media["audio"]) != 1:
        raise TimelineCompilerError("A1 voice stream is ambiguous in media_info.json")
    stream = media["audio"][0]
    audio_end = None if stream["duration_us"] is None else stream["start_us"] + stream["duration_us"]
    for item in mappings:
        source = item["source"]
        if source["start_us"] < stream["start_us"] or (audio_end is not None and source["end_us"] > audio_end):
            raise TimelineCompilerError("A1 SOURCE interval is outside the selected audio stream")
    return [{"id": f"a1_{index:06d}", "type": "SOURCE_AUDIO", "media_path": media["path"],
             "media_sha256": media["sha256"], "stream_index": stream["stream_index"],
             "source_start_us": item["source"]["start_us"], "source_end_us": item["source"]["end_us"],
             "cut_start_us": item["target"]["start_us"], "cut_end_us": item["target"]["end_us"],
             "timeline_start_us": item["target"]["start_us"], "timeline_end_us": item["target"]["end_us"]}
            for index, item in enumerate(mappings)]


def music_events(music_plan, asset_index, mappings, duration_us):
    events = []
    if music_plan["asset_request"] is None:
        return events
    request = asset_index.request("M8:music000000", "M8")
    if request["origin_id"] != "music000000" or request["cut_start_us"] != music_plan["regions"][0]["cut_start_us"] or request["cut_end_us"] != music_plan["regions"][0]["cut_end_us"]:
        raise TimelineCompilerError("M6 music request disagrees with the music plan")
    resolved = asset_index.resolved(request, "MUSIC")
    if resolved is None:
        return events
    asset, path = resolved
    for region in music_plan["regions"]:
        require_cut_range(region["cut_start_us"], region["cut_end_us"], duration_us, region["id"])
        if region["source_intervals"] != cut_range_to_source_ranges(
                region["cut_start_us"], region["cut_end_us"], mappings):
            raise TimelineCompilerError(f"{region['id']}: mapping between SOURCE and CUT is impossible")
        levels = []
        for level in music_plan["level_regions"]:
            if level["cut_start_us"] < region["cut_end_us"] and region["cut_start_us"] < level["cut_end_us"]:
                require_cut_range(level["cut_start_us"], level["cut_end_us"], duration_us, "music level")
                if level["source_intervals"] != cut_range_to_source_ranges(
                        level["cut_start_us"], level["cut_end_us"], mappings):
                    raise TimelineCompilerError("Music level mapping between SOURCE and CUT is impossible")
                levels.append({"cut_start_us": level["cut_start_us"], "cut_end_us": level["cut_end_us"],
                               "timeline_start_us": level["cut_start_us"], "timeline_end_us": level["cut_end_us"],
                               "source_intervals": level["source_intervals"], "mode": level["mode"],
                               "gain_db": level["gain_db"], "reason": level["reason"]})
        events.append({"id": f"a2_{len(events):06d}", "type": "MUSIC_ASSET", "origin_id": region["id"],
                       "asset_id": asset["asset_id"], "asset_path": str(path), "asset_sha256": asset["sha256"],
                       "source_intervals": region["source_intervals"],
                       "cut_start_us": region["cut_start_us"], "cut_end_us": region["cut_end_us"],
                       "timeline_start_us": region["cut_start_us"], "timeline_end_us": region["cut_end_us"],
                       "fade_in_us": region["fade_in_us"], "fade_out_us": region["fade_out_us"],
                       "level_regions": levels})
    return events


def sfx_events(sound_plan, asset_index, mappings, duration_us):
    events = []
    for item in sound_plan["decisions"]:
        if item["status"] == "NONE":
            continue
        request = asset_index.request(f"M7:{item['id']}", "M7")
        if request["origin_id"] != item["id"] or request["source_time_us"] != item["source_time_us"] or request["cut_time_us"] != item["cut_time_us"]:
            raise TimelineCompilerError(f"M6 request M7:{item['id']} disagrees with the sound plan")
        resolved = asset_index.resolved(request, "SFX")
        if resolved is None:
            continue
        asset, path = resolved
        projected = project_source_point(item["source_time_us"], mappings)
        if projected is None:
            raise TimelineCompilerError(f"{item['id']}: event is outside retained material")
        if projected != item["cut_time_us"]:
            raise TimelineCompilerError(f"{item['id']}: inconsistent SOURCE/CUT timestamps")
        asset_duration = asset["metadata"]["duration_us"]
        if type(asset_duration) is not int or asset_duration <= 0:
            raise TimelineCompilerError(f"{item['id']}: SFX duration <= 0 or unavailable")
        end = item["cut_time_us"] + asset_duration
        require_cut_range(item["cut_time_us"], end, duration_us, item["id"])
        events.append({"id": f"a3_{len(events):06d}", "type": "SFX_ASSET", "origin_id": item["id"],
                       "asset_id": asset["asset_id"], "asset_path": str(path), "asset_sha256": asset["sha256"],
                       "source_time_us": item["source_time_us"], "cut_time_us": item["cut_time_us"],
                       "timeline_start_us": item["cut_time_us"], "timeline_end_us": end,
                       "gain_db": item["gain_db"]})
    return events
