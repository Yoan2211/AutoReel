import hashlib
import json
from pathlib import Path

from modules.m6_asset_manager.manager import resolve_assets
from modules.m6_asset_manager.tests.fixtures import FakeProbe, add_asset, make_inputs


def dump(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def source_manifest(source_path):
    digest = hashlib.sha256(source_path.read_bytes()).hexdigest()
    return {"schema_version": "1.0.0", "module": {"id": "M0", "version": "1.0.0"},
            "source": {"path": str(source_path.resolve()), "size_bytes": source_path.stat().st_size,
                       "sha256": digest, "time_domain": "SOURCE", "start_us": 0,
                       "duration_us": 30_000_000, "duration_origin": "video_stream",
                       "video": {"stream_index": 0, "codec": "h264", "width": 1920, "height": 1080,
                                 "display_width": 1920, "display_height": 1080, "rotation_degrees": 0,
                                 "sample_aspect_ratio": "1:1", "avg_frame_rate": "30/1",
                                 "nominal_frame_rate": "30/1", "frame_timing": "UNDETERMINED",
                                 "pixel_format": "yuv420p", "color_primaries": None,
                                 "color_transfer": None, "color_space": None, "color_range": None,
                                 "dynamic_range": "SDR"},
                       "audio": [{"stream_index": 1, "codec": "aac", "sample_rate_hz": 48000,
                                  "channels": 2, "start_us": 0, "duration_us": 30_000_000}]},
            "warnings": []}


def rebind(paths):
    media_info, map_path, edit_path, camera_path, visual_path, sound_path, music_path, assets_path = paths
    source = load(media_info)["source"]
    media_path, media_hash = source["path"], source["sha256"]
    edit = load(edit_path); edit["source"].update(media_path=media_path, media_sha256=media_hash)
    edit_hash = dump(edit_path, edit)
    time_map = load(map_path); time_map["source"].update(media_path=media_path, media_sha256=media_hash,
                                                          edit_plan_sha256=edit_hash)
    map_hash = dump(map_path, time_map)
    media_info_hash = hashlib.sha256(media_info.read_bytes()).hexdigest()
    camera = load(camera_path)
    camera["source"].update(manifest_path=str(media_info.resolve()), manifest_sha256=media_info_hash,
                            smartedit_time_map_path=str(map_path.resolve()), smartedit_time_map_sha256=map_hash,
                            media_path=media_path, media_sha256=media_hash)
    camera["shots"] = []
    for index, mapping in enumerate(time_map["mappings"]):
        start, end = mapping["source"]["start_us"], mapping["source"]["end_us"]
        camera["shots"].append({"id": f"camera{index:06d}", "time_domain": "SOURCE",
          "source_start_us": start, "source_end_us": end,
          "keyframes": [{"source_us": start, "center_x": .5, "center_y": .5, "zoom": 1.03,
                         "crop_x": 656, "crop_y": 0, "crop_width": 608, "crop_height": 1080,
                         "subject_track_ids": [1], "predicted_track_ids": [], "warning": None}]})
    camera["summary"] = {"source_interval_count": len(camera["shots"]),
                         "frames_analyzed": len(camera["shots"]), "detections": len(camera["shots"]),
                         "keyframes": len(camera["shots"])}
    camera_hash = dump(camera_path, camera)
    visual = load(visual_path)
    visual["source"].update(edit_plan_sha256=edit_hash, smartedit_time_map_sha256=map_hash,
                            camera_plan_sha256=camera_hash, media_path=media_path, media_sha256=media_hash)
    visual_hash = dump(visual_path, visual)
    sound = load(sound_path)
    sound["source"].update(edit_plan_sha256=edit_hash, smartedit_time_map_sha256=map_hash,
                           camera_plan_sha256=camera_hash, visual_plan_sha256=visual_hash,
                           media_path=media_path, media_sha256=media_hash)
    sound_hash = dump(sound_path, sound)
    music = load(music_path)
    music["source"].update(edit_plan_sha256=edit_hash, smartedit_time_map_sha256=map_hash,
                           visual_plan_sha256=visual_hash, sound_plan_sha256=sound_hash,
                           media_path=media_path, media_sha256=media_hash)
    music_hash = dump(music_path, music)
    assets = load(assets_path)
    assets["source"].update(visual_plan_sha256=visual_hash, sound_plan_sha256=sound_hash,
                            music_plan_sha256=music_hash, media_path=media_path, media_sha256=media_hash)
    dump(assets_path, assets)


def make_compiler_inputs(root, *, mappings=((0, 7_000_000), (8_000_000, 17_200_000))):
    sentences = ["Imagine ce graphique médical avec 42 pourcent de résultat.",
                 "Le traitement médical compare 18 pourcent de progression.",
                 "La santé confirme 30 pourcent."]
    visual, sound, music, library, assets = make_inputs(root / "chain", sentences,
                                                         spacing_us=8_000_000, mappings=mappings)
    add_asset(library, "graphics/icon_graphic_pourcent_resultat.png")
    add_asset(library, "sfx/pop_visual.wav")
    add_asset(library, "music/clean_modern_medical_low.wav")
    resolve_assets(visual, sound, music, library, assets, project_root_path=root,
                   media_probe=CompilerProbe())
    visual_value = load(visual)
    edit = Path(visual_value["source"]["edit_plan_path"])
    time_map = Path(visual_value["source"]["smartedit_time_map_path"])
    camera = Path(visual_value["source"]["camera_plan_path"])
    source = root / "source.mp4"; source.write_bytes(b"immutable original source fixture")
    media_info = root / "media_info.json"; dump(media_info, source_manifest(source))
    paths = (media_info, time_map, edit, camera, visual, sound, music, assets)
    rebind(paths)
    return paths, root / "timeline_draft.json"
class CompilerProbe(FakeProbe):
    def probe(self, path, asset_type):
        value = super().probe(path, asset_type)
        if asset_type == "SFX":
            value["duration_us"] = 500_000
        elif asset_type == "MUSIC":
            value["duration_us"] = 20_000_000
        return value
