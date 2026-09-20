TYPE_MAP = {"ILLUSTRATION": "ILLUSTRATION", "PHOTO": "IMAGE", "BROLL": "BROLL",
            "ICON_GRAPHIC": "GRAPHIC"}


def collect_requests(visual, sound, music):
    result = []
    for item in visual["requests"]:
        if item["disposition"] == "NONE":
            continue
        result.append({"request_id": f"M5:{item['id']}", "origin_module": "M5", "origin_id": item["id"],
                       "asset_type": TYPE_MAP[item["media_type"]], "request_type": item["media_type"],
                       "query": item["concept"], "upstream_status": item["disposition"],
                       "desired_duration_us": item["desired_duration_us"],
                       "source_start_us": item["source_start_us"], "source_end_us": item["source_end_us"],
                       "cut_start_us": item["cut_start_us"], "cut_end_us": item["cut_end_us"],
                       "source_time_us": None, "cut_time_us": None})
    for item in sound["decisions"]:
        if item["status"] == "NONE":
            continue
        result.append({"request_id": f"M7:{item['id']}", "origin_module": "M7", "origin_id": item["id"],
                       "asset_type": "SFX", "request_type": item["type"],
                       "query": item["event_kind"], "upstream_status": item["status"],
                       "desired_duration_us": None, "source_start_us": None, "source_end_us": None,
                       "cut_start_us": None, "cut_end_us": None,
                       "source_time_us": item["source_time_us"], "cut_time_us": item["cut_time_us"]})
    if music["asset_request"] is not None:
        request = music["asset_request"]
        region = music["regions"][0]
        result.append({"request_id": "M8:music000000", "origin_module": "M8", "origin_id": "music000000",
                       "asset_type": "MUSIC", "request_type": request["mood"],
                       "query": f"{request['mood']} {request['energy']}", "upstream_status": request["status"],
                       "desired_duration_us": request["desired_duration_us"],
                       "source_start_us": None, "source_end_us": None,
                       "cut_start_us": region["cut_start_us"], "cut_end_us": region["cut_end_us"],
                       "source_time_us": None, "cut_time_us": None})
    return result
