from pathlib import Path

from core.time_ranges import cut_range_to_source_ranges

from .config import MusicPlannerConfig
from .context import analyze
from .contracts import load_inputs, validate
from .decision import decide
from .levels import build_level_regions, speech_ranges
from .output import write


def plan_music(transcript_path, edit_plan_path, smartedit_time_map_path,
               visual_plan_path, sound_plan_path, music_plan_path, config=None):
    config = config or MusicPlannerConfig()
    inputs = [Path(item).resolve(strict=True) for item in
              (transcript_path, edit_plan_path, smartedit_time_map_path, visual_plan_path, sound_plan_path)]
    output = Path(music_plan_path).absolute()
    if output in inputs:
        raise FileExistsError("Music plan must not overwrite an input")
    if output.exists() or output.is_symlink():
        raise FileExistsError(f"Music plan exists: {output}")
    transcript, edit, time_map, visual, sound, hashes = load_inputs(*inputs)
    duration = time_map["output_duration_us"]
    mood, energy, mood_confidence, mood_reason = analyze(edit, visual)
    status, confidence, decision_reason = decide(transcript, duration, mood_confidence, config)
    regions = []
    levels = []
    request = None
    if status != "NONE":
        fade_in = min(config.fade_in_us, duration // 2)
        fade_out = min(config.fade_out_us, duration // 2)
        regions = [{"id": "music000000", "cut_start_us": 0, "cut_end_us": duration,
                    "source_intervals": cut_range_to_source_ranges(0, duration, time_map["mappings"]),
                    "mood": mood, "energy": energy, "speech_gain_db": config.speech_gain_db,
                    "no_speech_gain_db": config.no_speech_gain_db,
                    "fade_in_us": fade_in, "fade_out_us": fade_out,
                    "strategy": "STABLE_BED",
                    "reason": "One continuous bed avoids reacting to every edit or micro-event"}]
        speech = speech_ranges(transcript, time_map["mappings"], config.speech_merge_gap_us)
        levels = build_level_regions(duration, speech, sound, time_map["mappings"], config)
        request = {"kind": "MUSIC", "status": status, "mood": mood, "energy": energy,
                   "desired_duration_us": duration, "seamless_loop_acceptable": True,
                   "reason": f"{decision_reason}; {mood_reason}"}
    source = {"transcript_path": str(inputs[0]), "transcript_sha256": hashes["transcript_sha256"],
              "edit_plan_path": str(inputs[1]), "edit_plan_sha256": hashes["edit_plan_sha256"],
              "smartedit_time_map_path": str(inputs[2]), "smartedit_time_map_sha256": hashes["smartedit_time_map_sha256"],
              "visual_plan_path": str(inputs[3]), "visual_plan_sha256": hashes["visual_plan_sha256"],
              "sound_plan_path": str(inputs[4]), "sound_plan_sha256": hashes["sound_plan_sha256"],
              "media_path": edit["source"]["media_path"], "media_sha256": edit["source"]["media_sha256"]}
    plan = {"schema_version": "1.0.0", "module": {"id": "M8", "version": "1.0.0"},
            "stage": "music_planner", "source_time_domain": "SOURCE", "target_time_domain": "CUT",
            "source": source, "policy": config.to_contract(),
            "decision": {"status": status, "mood": mood if status != "NONE" else None,
                         "energy": energy if status != "NONE" else "NONE",
                         "confidence": confidence, "reason": decision_reason},
            "asset_request": request, "regions": regions, "level_regions": levels,
            "summary": {"music_region_count": len(regions), "level_region_count": len(levels),
                        "speech_duck_count": sum(item["mode"] == "SPEECH_DUCK" for item in levels),
                        "no_speech_lift_count": sum(item["mode"] == "NO_SPEECH_LIFT" for item in levels),
                        "sfx_protected_count": sum(item["mode"] == "SFX_PROTECTED" for item in levels)},
            "warnings": ["MUSIC_NOT_RECOMMENDED"] if status == "NONE" else []}
    validate(plan, "music-plan-1.0.0.json")
    write(output, plan)
    return plan
