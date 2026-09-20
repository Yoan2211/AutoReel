from pathlib import Path

from .collection import collect
from .config import SoundDesignConfig
from .contracts import load_inputs, validate
from .output import write
from .prioritization import resolve


def _confidence(score):
    return "HIGH" if score >= .82 else "MEDIUM" if score >= .7 else "LOW"


def plan_sounds(transcript_path, edit_plan_path, visual_plan_path, camera_plan_path,
                smartedit_time_map_path, sound_plan_path, config=None):
    config = config or SoundDesignConfig()
    inputs = [Path(item).resolve(strict=True) for item in
              (transcript_path, edit_plan_path, visual_plan_path, camera_plan_path, smartedit_time_map_path)]
    output = Path(sound_plan_path).absolute()
    if output in inputs:
        raise FileExistsError("Sound plan must not overwrite an input")
    if output.exists() or output.is_symlink():
        raise FileExistsError(f"Sound plan exists: {output}")
    transcript, edit, visual, camera, time_map, hashes = load_inputs(*inputs)
    events = collect(edit, visual, camera, time_map, config)
    classified, kept_ids, conflict_losers, density_losers = resolve(events, config)
    decisions = []
    for index, item in enumerate(sorted(classified, key=lambda value: (value.event.cut_time_us, value.event.id))):
        event = item.event
        status, sound_type, gain, reason = "NONE", "NONE", None, item.reason
        if event.id in conflict_losers:
            reason = f"No SFX: conflicts with higher-priority {conflict_losers[event.id]}; {item.reason}"
        elif event.id in density_losers:
            reason = f"No SFX: suppressed by spacing or density policy; {item.reason}"
        elif event.id not in kept_ids or event.score < config.review_threshold:
            reason = f"No SFX: confidence is below the review threshold; {item.reason}"
        else:
            status = "PROPOSED" if event.score >= config.proposal_threshold else "REVIEW"
            sound_type, gain = item.sound_type, item.gain_db
        decisions.append({"id": f"sound{index:06d}", "candidate_id": event.id,
                          "event_kind": event.kind, "type": sound_type, "status": status,
                          "source_time_us": event.source_time_us, "cut_time_us": event.cut_time_us,
                          "gain_db": gain, "priority": _confidence(event.score),
                          "confidence": _confidence(event.score), "score": event.score,
                          "origin_ids": list(event.origin_ids), "reason": reason})
    active = [item for item in decisions if item["status"] != "NONE"]
    source = {"transcript_path": str(inputs[0]), "transcript_sha256": hashes["transcript_sha256"],
              "edit_plan_path": str(inputs[1]), "edit_plan_sha256": hashes["edit_plan_sha256"],
              "visual_plan_path": str(inputs[2]), "visual_plan_sha256": hashes["visual_plan_sha256"],
              "camera_plan_path": str(inputs[3]), "camera_plan_sha256": hashes["camera_plan_sha256"],
              "smartedit_time_map_path": str(inputs[4]), "smartedit_time_map_sha256": hashes["smartedit_time_map_sha256"],
              "media_path": edit["source"]["media_path"], "media_sha256": edit["source"]["media_sha256"]}
    plan = {"schema_version": "1.0.0", "module": {"id": "M7", "version": "1.0.0"},
            "stage": "sounddesign", "source_time_domain": "SOURCE", "target_time_domain": "CUT",
            "source": source, "policy": config.to_contract(), "decisions": decisions,
            "summary": {"candidate_count": len(events), "proposed_count": sum(item["status"] == "PROPOSED" for item in decisions),
                        "review_count": sum(item["status"] == "REVIEW" for item in decisions),
                        "none_count": sum(item["status"] == "NONE" for item in decisions)},
            "warnings": (["NO_SPEECH_RECOGNIZED"] if transcript["status"] == "no_speech_recognized" else []) +
                        (["NO_SFX_SELECTED"] if transcript["status"] != "no_speech_recognized" and not active else [])}
    validate(plan, "sound-plan-1.0.0.json")
    write(output, plan)
    return plan
