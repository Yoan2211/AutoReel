import json

from modules.m5_visual_planner.config import VisualPlannerConfig
from modules.m5_visual_planner.planner import plan_visuals
from modules.m5_visual_planner.tests.fixtures import dump, make_camera, make_inputs


VISUAL_CONFIG = VisualPlannerConfig(minimum_gap_us=1, minimum_duration_us=500_000)


def make_chain(root, sentences, *, spacing_us=5_000_000, section_groups=None,
               mappings=None, keyframes=None):
    paths = make_inputs(root, sentences, spacing_us=spacing_us,
                        section_groups=section_groups, mappings=mappings)
    edit_path, transcript_path, map_path, visual_path = paths[:4]
    camera_path = make_camera(root / "camera-plan.json", map_path, paths[6])
    if keyframes:
        camera = json.loads(camera_path.read_text(encoding="utf-8"))
        camera["shots"] = [{"id": "camera000000", "time_domain": "SOURCE",
                            "source_start_us": 0, "source_end_us": paths[5]["source_end_us"],
                            "keyframes": keyframes}]
        camera["summary"] = {"source_interval_count": 1, "frames_analyzed": len(keyframes),
                             "detections": len(keyframes), "keyframes": len(keyframes)}
        dump(camera_path, camera)
    plan_visuals(edit_path, transcript_path, map_path, visual_path,
                 camera_plan_path=camera_path, config=VISUAL_CONFIG)
    return transcript_path, edit_path, visual_path, camera_path, map_path, root / "sound-plan.json"


def keyframe(source_us, zoom):
    return {"source_us": source_us, "center_x": .5, "center_y": .5, "zoom": zoom,
            "crop_x": 0, "crop_y": 0, "crop_width": 1080, "crop_height": 1920,
            "subject_track_ids": [1], "predicted_track_ids": [], "warning": None}
