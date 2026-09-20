from __future__ import annotations

from fractions import Fraction
from pathlib import Path
from typing import Any

from .contracts import load_source_manifest, verify_all_media
from .time_conversion import interval_us_to_frames, parse_fps, us_to_frame


def _track_map(timeline: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {track["id"]: track for track in timeline["tracks"]}


def _source_fps(manifest: dict[str, Any]) -> Fraction:
    video = manifest["source"]["video"]
    raw = video.get("avg_frame_rate") or video.get("nominal_frame_rate")
    if not raw or raw in {"0/0", "N/A"}:
        raise ValueError("Source manifest has no usable frame rate")
    return parse_fps(str(raw))


def build_plan(
    timeline_path: Path,
    timeline: dict[str, Any],
    timeline_sha256: str,
    *,
    expected_fps: str,
    timeline_name: str,
    report_path: Path,
    srt_path: Path,
) -> dict[str, Any]:
    target_fps = parse_fps(expected_fps)
    _manifest_path, manifest = load_source_manifest(timeline_path, timeline)
    source_fps = _source_fps(manifest)
    resolved = verify_all_media(timeline_path, timeline)
    tracks = _track_map(timeline)

    plan_tracks: dict[str, list[dict]] = {
        key: [] for key in ("V1", "V2", "V3", "A1", "A2", "A3")
    }

    for track_id in ("V1", "V2", "V3", "A1", "A2", "A3"):
        for event in tracks[track_id]["events"]:
            row = dict(event)
            raw = event.get("media_path") or event.get("asset_path")
            row["physical_path"] = str(resolved[str(raw)]) if raw is not None else None
            row["record_start_frame"] = us_to_frame(event["timeline_start_us"], target_fps)
            row["record_end_frame"] = us_to_frame(event["timeline_end_us"], target_fps)
            if row["record_end_frame"] <= row["record_start_frame"]:
                row["record_end_frame"] = row["record_start_frame"] + 1

            if event["type"] in {"SOURCE_VIDEO", "SOURCE_AUDIO"}:
                src_start, src_end = interval_us_to_frames(
                    event["source_start_us"], event["source_end_us"], source_fps
                )
                row["source_start_frame"] = src_start
                row["source_end_frame"] = src_end
            elif event["type"] in {"VISUAL_ASSET", "MUSIC_ASSET", "SFX_ASSET"}:
                row["source_start_frame"] = 0
                row["source_end_frame"] = max(
                    1, row["record_end_frame"] - row["record_start_frame"]
                )

            if event["type"] == "SOURCE_VIDEO":
                keyframes = []
                for keyframe in event.get("camera_keyframes", []):
                    kf = dict(keyframe)
                    kf["clip_offset_frame"] = max(
                        0,
                        us_to_frame(
                            keyframe["timeline_us"] - event["timeline_start_us"],
                            target_fps,
                        ),
                    )
                    keyframes.append(kf)
                row["camera_keyframes"] = keyframes

            if event["type"] == "MUSIC_ASSET":
                levels = []
                for level in event.get("level_regions", []):
                    lv = dict(level)
                    lv["clip_offset_frame"] = max(
                        0,
                        us_to_frame(
                            level["timeline_start_us"] - event["timeline_start_us"],
                            target_fps,
                        ),
                    )
                    levels.append(lv)
                row["level_regions"] = levels

            plan_tracks[track_id].append(row)

    video = manifest["source"]["video"]
    return {
        "module": {"id": "M11", "version": "1.0.0"},
        "timeline_json_path": str(timeline_path),
        "timeline_json_sha256": timeline_sha256,
        "timeline_name_base": timeline_name,
        "expected_fps": {
            "numerator": target_fps.numerator,
            "denominator": target_fps.denominator,
            "display": f"{float(target_fps):.6f}".rstrip("0").rstrip("."),
        },
        "source_fps": {
            "numerator": source_fps.numerator,
            "denominator": source_fps.denominator,
            "display": f"{float(source_fps):.6f}".rstrip("0").rstrip("."),
        },
        "format": timeline["format"],
        "source_geometry": {
            "display_width": video["display_width"],
            "display_height": video["display_height"],
            "rotation_degrees": video["rotation_degrees"],
        },
        "tracks": plan_tracks,
        "report_path": str(report_path),
        "srt_path": str(srt_path),
    }
