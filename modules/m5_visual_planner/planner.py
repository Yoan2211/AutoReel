from pathlib import Path

from .concepts import detect
from .config import VisualPlannerConfig
from .contracts import load_inputs, validate
from .output import write
from .selection import select
from .time_mapping import best_retained_window


def _level(score):
    return "HIGH" if score >= .85 else "MEDIUM" if score >= .7 else "LOW"


def _request(request_id, passage, section_id, candidate, window, selected, config, rejection=None):
    if candidate is None or not selected:
        source_start, source_end, cut_start, cut_end = window or (
            passage["source_start_us"], passage["source_end_us"], None, None)
        return {"id": request_id, "passage_id": passage["id"], "section_id": section_id,
                "disposition": "NONE", "media_type": "NONE", "concept": None,
                "source_start_us": source_start, "source_end_us": source_end,
                "cut_start_us": cut_start, "cut_end_us": cut_end, "desired_duration_us": 0,
                "priority": "NONE", "confidence": "LOW",
                "reason": rejection or "No sufficiently concrete visual concept; talking-head framing remains clearer"}
    available = candidate.cut_end_us - candidate.cut_start_us
    duration = min(config.target_duration_us, config.maximum_duration_us, available)
    source_end = candidate.source_start_us + duration
    cut_end = candidate.cut_start_us + duration
    confidence = _level(candidate.score)
    return {"id": request_id, "passage_id": passage["id"], "section_id": section_id,
            "disposition": "AUTO" if candidate.score >= config.auto_confidence_threshold else "REVIEW",
            "media_type": candidate.media_type, "concept": candidate.concept,
            "source_start_us": candidate.source_start_us, "source_end_us": source_end,
            "cut_start_us": candidate.cut_start_us, "cut_end_us": cut_end,
            "desired_duration_us": duration, "priority": confidence, "confidence": confidence,
            "reason": candidate.reason}


def plan_visuals(edit_plan_path, transcript_path, smartedit_time_map_path,
                 visual_plan_path, camera_plan_path=None, config=None):
    config = config or VisualPlannerConfig()
    required = [Path(item).resolve(strict=True) for item in
                (edit_plan_path, transcript_path, smartedit_time_map_path)]
    camera_path = Path(camera_plan_path).resolve(strict=True) if camera_plan_path else None
    output_path = Path(visual_plan_path).absolute()
    if output_path in required or output_path == camera_path:
        raise FileExistsError("Visual plan must not overwrite an input")
    edit, transcript, time_map, camera, edit_hash, transcript_hash, map_hash, camera_hash = load_inputs(
        required[0], required[1], required[2], camera_path)
    section_by_passage = {}
    terms_by_section = {}
    for section in edit["sections"]:
        terms_by_section[section["id"]] = section["theme_terms"]
        for passage_id in section["passage_ids"]:
            section_by_passage[passage_id] = section["id"]
    roles = {}
    for role in edit["roles"]:
        roles.setdefault(role["passage_id"], set()).add(role["role"])
    candidates = []
    windows = {}
    short_passages = set()
    for passage in edit["passages"]:
        window = best_retained_window(passage["source_start_us"], passage["source_end_us"], time_map["mappings"])
        windows[passage["id"]] = window
        section_id = section_by_passage.get(passage["id"], "unsectioned")
        if window is None or window[1] - window[0] < config.minimum_duration_us:
            short_passages.add(passage["id"])
            continue
        candidate = detect(passage, section_id, terms_by_section.get(section_id, []), window,
                           roles.get(passage["id"], set()))
        if candidate:
            candidates.append(candidate)
    chosen = select(candidates, config)
    chosen_ids = {item.passage_id for item in chosen}
    candidate_by_id = {item.passage_id: item for item in candidates}
    requests = []
    for index, passage in enumerate(edit["passages"]):
        section_id = section_by_passage.get(passage["id"], "unsectioned")
        candidate = candidate_by_id.get(passage["id"])
        rejection = None
        if passage["id"] in short_passages:
            rejection = "Retained passage is shorter than the minimum useful visual duration"
        elif candidate and passage["id"] not in chosen_ids:
            rejection = "Candidate suppressed by spacing or section density policy"
        requests.append(_request(f"visual{index:06d}", passage, section_id, candidate,
                                 windows.get(passage["id"]),
                                 passage["id"] in chosen_ids, config, rejection))
    source = {"edit_plan_path": str(required[0]), "edit_plan_sha256": edit_hash,
              "transcript_path": str(required[1]), "transcript_sha256": transcript_hash,
              "smartedit_time_map_path": str(required[2]), "smartedit_time_map_sha256": map_hash,
              "camera_plan_path": str(camera_path) if camera_path else None,
              "camera_plan_sha256": camera_hash,
              "media_path": edit["source"]["media_path"], "media_sha256": edit["source"]["media_sha256"]}
    selected_requests = [item for item in requests if item["disposition"] != "NONE"]
    plan = {"schema_version": "1.0.0", "module": {"id": "M5", "version": "1.0.0"},
            "stage": "visual_planner", "source_time_domain": "SOURCE", "target_time_domain": "CUT",
            "source": source, "policy": config.to_contract(), "requests": requests,
            "summary": {"passage_count": len(edit["passages"]), "candidate_count": len(candidates),
                        "selected_count": len(selected_requests),
                        "auto_count": sum(item["disposition"] == "AUTO" for item in selected_requests),
                        "review_count": sum(item["disposition"] == "REVIEW" for item in selected_requests),
                        "none_count": sum(item["disposition"] == "NONE" for item in requests)},
            "warnings": (["NO_SPEECH_RECOGNIZED"] if not edit["passages"] else []) +
                        (["NO_VISUALS_SELECTED"] if edit["passages"] and not selected_requests else [])}
    validate(plan, "visual-plan-1.0.0.json")
    write(output_path, plan)
    return plan
