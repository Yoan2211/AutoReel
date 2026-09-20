from pathlib import Path

from .assets import AssetIndex, non_materialized
from .audio import music_events, sfx_events, source_audio_events
from .camera import camera_by_clip
from .contracts import load_inputs, validate_draft
from .errors import TimelineCompilerError
from .output import write_exclusive
from .validation import TRACKS, validate_tracks, verify_source
from .video import source_video_events, visual_events


def _track(track_id, events):
    spec = next(item for item in TRACKS if item[0] == track_id)
    return {"id": spec[0], "kind": spec[1], "index": spec[2], "role": spec[3], "events": events}


def compile_pass_a(media_info_path, smartedit_time_map_path, edit_plan_path, camera_plan_path,
                   visual_plan_path, sound_plan_path, music_plan_path, assets_manifest_path,
                   timeline_draft_path):
    inputs = (media_info_path, smartedit_time_map_path, edit_plan_path, camera_plan_path,
              visual_plan_path, sound_plan_path, music_plan_path, assets_manifest_path)
    output = Path(timeline_draft_path).absolute()
    input_paths = [Path(item).resolve(strict=True) for item in inputs]
    if output in input_paths or output.exists() or output.is_symlink():
        raise FileExistsError(f"Timeline draft must be a new file: {output}")
    values, paths, hashes = load_inputs(input_paths)
    media_info, time_map, _edit, camera, visual, sound, music, assets = values
    media = media_info["source"]
    verify_source(media)
    mappings, duration = time_map["mappings"], time_map["output_duration_us"]
    v1_ids = [f"v1_{index:06d}" for index in range(len(mappings))]
    camera_keyframes = camera_by_clip(camera, mappings, v1_ids)
    asset_index = AssetIndex(assets)
    tracks = [
        _track("V1", source_video_events(media, mappings, camera_keyframes)),
        _track("V2", visual_events(visual, asset_index, mappings, duration)),
        _track("V3", []),
        _track("A1", source_audio_events(media, mappings)),
        _track("A2", music_events(music, asset_index, mappings, duration)),
        _track("A3", sfx_events(sound, asset_index, mappings, duration)),
    ]
    validate_tracks(tracks, duration)
    source_names = ("media_info", "smartedit_time_map", "edit_plan", "camera_plan",
                    "visual_plan", "sound_plan", "music_plan", "assets_manifest")
    draft = {
        "schema_version": "1.0.0", "module": {"id": "M10", "version": "1.0.0"},
        "stage": "timeline_compiler_pass_a",
        "time_domains": {"source": "SOURCE", "cut": "CUT", "timeline": "TIMELINE"},
        "source": {f"{name}_path": str(path) for name, path in zip(source_names, paths)} |
                  {f"{name}_sha256": digest for name, digest in zip(source_names, hashes)},
        "format": {"width": 1080, "height": 1920, "aspect_ratio": "9:16",
                   "duration_us": duration, "timeline_start_us": 0},
        "tracks": tracks, "unmaterialized": non_materialized(assets), "diagnostics": [],
    }
    draft["summary"] = {
        "track_count": len(tracks), "event_count": sum(len(item["events"]) for item in tracks),
        "source_segment_count": len(mappings),
        "materialized_asset_event_count": sum(len(item["events"]) for item in tracks if item["id"] in {"V2", "A2", "A3"}),
        "unmaterialized_count": len(draft["unmaterialized"]), "diagnostic_count": 0}
    validate_draft(draft)
    write_exclusive(output, draft)
    return draft
