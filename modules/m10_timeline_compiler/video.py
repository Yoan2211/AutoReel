from .projection import require_cut_range, require_exact_projection


def source_video_events(media, mappings, camera):
    events = []
    for index, item in enumerate(mappings):
        source, cut = item["source"], item["target"]
        event_id = f"v1_{index:06d}"
        events.append({"id": event_id, "type": "SOURCE_VIDEO", "media_path": media["path"],
                       "media_sha256": media["sha256"],
                       "source_start_us": source["start_us"], "source_end_us": source["end_us"],
                       "cut_start_us": cut["start_us"], "cut_end_us": cut["end_us"],
                       "timeline_start_us": cut["start_us"], "timeline_end_us": cut["end_us"],
                       "camera_keyframes": camera[event_id]})
    return events


def visual_events(visual_plan, asset_index, mappings, duration_us):
    events = []
    for item in visual_plan["requests"]:
        if item["disposition"] == "NONE":
            continue
        request = asset_index.request(f"M5:{item['id']}", "M5")
        expected_type = {"PHOTO": "IMAGE", "ILLUSTRATION": "ILLUSTRATION",
                         "BROLL": "BROLL", "ICON_GRAPHIC": "GRAPHIC"}[item["media_type"]]
        expected_request = (item["source_start_us"], item["source_end_us"], item["cut_start_us"],
                            item["cut_end_us"], item["desired_duration_us"])
        actual_request = (request["source_start_us"], request["source_end_us"], request["cut_start_us"],
                          request["cut_end_us"], request["desired_duration_us"])
        if actual_request != expected_request or request["origin_id"] != item["id"]:
            raise TimelineCompilerError(f"M6 request M5:{item['id']} disagrees with the visual plan")
        resolved = asset_index.resolved(request, expected_type)
        if resolved is None:
            continue
        asset, path = resolved
        require_cut_range(item["cut_start_us"], item["cut_end_us"], duration_us, item["id"])
        require_exact_projection(item["source_start_us"], item["source_end_us"],
                                 item["cut_start_us"], item["cut_end_us"], mappings, item["id"])
        events.append({"id": f"v2_{len(events):06d}", "type": "VISUAL_ASSET",
                       "origin_id": item["id"], "asset_id": asset["asset_id"], "asset_path": str(path),
                       "asset_sha256": asset["sha256"], "asset_type": asset["asset_type"],
                       "source_start_us": item["source_start_us"], "source_end_us": item["source_end_us"],
                       "cut_start_us": item["cut_start_us"], "cut_end_us": item["cut_end_us"],
                       "timeline_start_us": item["cut_start_us"], "timeline_end_us": item["cut_end_us"]})
    return events
