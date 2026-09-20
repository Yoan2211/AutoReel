from pathlib import Path

from .config import AutoCamConfig
from .contracts import load_inputs, validate, verify_media
from .detector import OpenCVSubjectDetector
from .frames import OpenCVFrameProvider
from .framing import calculate
from .output import write
from .smoothing import CameraSmoother, should_keyframe
from .tracking import SubjectTracker


def _keyframe(frame, state, subjects, display_width, display_height):
    crop_w, crop_h = state.crop_width*display_width, state.crop_height*display_height
    return {"source_us": frame.source_us, "center_x": round(state.center_x, 6),
            "center_y": round(state.center_y, 6), "zoom": round(state.zoom, 6),
            "crop_x": max(0, round(state.center_x*display_width-crop_w/2)),
            "crop_y": max(0, round(state.center_y*display_height-crop_h/2)),
            "crop_width": min(display_width, round(crop_w)),
            "crop_height": min(display_height, round(crop_h)),
            "subject_track_ids": [item[0] for item in subjects],
            "predicted_track_ids": [item[0] for item in subjects if item[2]],
            "warning": state.warning}


def autocam(source_manifest_path, smartedit_time_map_path, camera_plan_path,
            config=None, *, frame_provider=None, detector=None):
    config = config or AutoCamConfig()
    manifest_path = Path(source_manifest_path).resolve(strict=True)
    map_path = Path(smartedit_time_map_path).resolve(strict=True)
    destination = Path(camera_plan_path).absolute()
    if destination in (manifest_path, map_path): raise FileExistsError("Camera plan must not overwrite an input")
    manifest, time_map, manifest_hash, map_hash = load_inputs(manifest_path, map_path)
    source = manifest["source"]; media_path, initial_signature = verify_media(source)
    video = source["video"]; display_w, display_h = video["display_width"], video["display_height"]
    provider = frame_provider or OpenCVFrameProvider()
    detector = detector or OpenCVSubjectDetector(config.device, config.cpu_fallback)
    tracker, smoother = SubjectTracker(config.lost_hold_us), CameraSmoother(config.smoothing_alpha)
    shots, warnings, frames_analyzed, detections_count = [], set(getattr(detector, "warnings", [])), 0, 0
    intervals = [(item["source"]["start_us"], item["source"]["end_us"]) for item in time_map["mappings"]]
    if not intervals:
        warnings.add("NO_FRAMES_ANALYZED")
    for shot_index, (start_us, end_us) in enumerate(intervals):
        tracker.reset(); smoother.reset(); keyframes = []; previous_state = None; previous_us = start_us
        for frame in provider.frames(media_path, [(start_us, end_us)], source["start_us"],
                                     video["rotation_degrees"], config.sample_interval_us):
            if not start_us <= frame.source_us < end_us:
                raise ValueError("Frame provider returned a deleted SOURCE timestamp")
            detections = detector.detect(frame); frames_analyzed += 1; detections_count += len(detections)
            subjects = tracker.update(frame.source_us, detections)
            raw = calculate(frame.width, frame.height, subjects, config); state = smoother.update(raw)
            if raw.warning: warnings.add(raw.warning)
            if should_keyframe(previous_state, state, previous_us, frame.source_us, config):
                keyframes.append(_keyframe(frame, state, subjects, display_w, display_h))
                previous_state, previous_us = state, frame.source_us
        if not keyframes:
            warnings.add("NO_FRAMES_ANALYZED")
        shots.append({"id": f"camera{shot_index:06d}", "time_domain": "SOURCE",
                      "source_start_us": start_us, "source_end_us": end_us,
                      "keyframes": keyframes})
    plan = {"schema_version": "1.0.0", "module": {"id": "M4", "version": "1.0.0"},
            "stage": "autocam", "time_domain": "SOURCE",
            "source": {"manifest_path": str(manifest_path), "manifest_sha256": manifest_hash,
                       "smartedit_time_map_path": str(map_path), "smartedit_time_map_sha256": map_hash,
                       "media_path": source["path"], "media_sha256": source["sha256"]},
            "output": {"width": config.output_width, "height": config.output_height,
                       "aspect_ratio": "9:16"},
            "input_geometry": {"encoded_width": video["width"], "encoded_height": video["height"],
                               "display_width": display_w, "display_height": display_h,
                               "rotation_degrees": video["rotation_degrees"]},
            "engine": {"detector": detector.name, "detector_version": detector.version,
                       "device": detector.device, "frame_provider": type(provider).__name__},
            "policy": config.to_contract(), "shots": shots,
            "summary": {"source_interval_count": len(intervals), "frames_analyzed": frames_analyzed,
                        "detections": detections_count, "keyframes": sum(len(x["keyframes"]) for x in shots)},
            "warnings": sorted(warnings)}
    _, final_signature = verify_media(source)
    if final_signature != initial_signature:
        raise OSError("Original SOURCE file changed during AutoCam analysis")
    validate(plan, "camera-plan-1.0.0.json"); write(destination, plan); return plan
