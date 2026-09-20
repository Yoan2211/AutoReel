from .errors import TimelineCompilerError
from .projection import project_source_point, project_source_range


def camera_by_clip(camera_plan, mappings, clip_ids):
    result = {clip_id: [] for clip_id in clip_ids}
    ordered_shots = sorted(camera_plan["shots"], key=lambda item: item["source_start_us"])
    if ordered_shots != camera_plan["shots"] or any(
            left["source_end_us"] > right["source_start_us"] for left, right in zip(ordered_shots, ordered_shots[1:])):
        raise TimelineCompilerError("Camera shots overlap or are unordered")
    for shot in camera_plan["shots"]:
        pieces = project_source_range(shot["source_start_us"], shot["source_end_us"], mappings)
        covered = sum(item[1] - item[0] for item in pieces)
        if covered != shot["source_end_us"] - shot["source_start_us"]:
            raise TimelineCompilerError(f"Camera shot {shot['id']} is outside retained material")
        for keyframe in shot["keyframes"]:
            if not shot["source_start_us"] <= keyframe["source_us"] <= shot["source_end_us"]:
                raise TimelineCompilerError(f"Camera keyframe in {shot['id']} is outside its shot")
            cut_us = project_source_point(keyframe["source_us"], mappings, allow_program_end=True)
            if cut_us is None:
                raise TimelineCompilerError(f"Camera keyframe in {shot['id']} is outside retained material")
            match = None
            for index, item in enumerate(mappings):
                source = item["source"]
                if source["start_us"] <= keyframe["source_us"] < source["end_us"]:
                    match = index
                    break
                if index == len(mappings) - 1 and keyframe["source_us"] == source["end_us"]:
                    match = index
            if match is None:
                raise TimelineCompilerError("Camera mapping is impossible")
            result[clip_ids[match]].append({
                "source_us": keyframe["source_us"], "cut_us": cut_us, "timeline_us": cut_us,
                "center_x": keyframe["center_x"], "center_y": keyframe["center_y"],
                "zoom": keyframe["zoom"], "crop_x": keyframe["crop_x"], "crop_y": keyframe["crop_y"],
                "crop_width": keyframe["crop_width"], "crop_height": keyframe["crop_height"],
                "subject_track_ids": keyframe["subject_track_ids"],
                "predicted_track_ids": keyframe["predicted_track_ids"], "warning": keyframe["warning"]})
    for values in result.values():
        values.sort(key=lambda item: item["source_us"])
        if any(left["source_us"] >= right["source_us"] for left, right in zip(values, values[1:])):
            raise TimelineCompilerError("Camera keyframes overlap or are unordered")
    return result
