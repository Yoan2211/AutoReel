import hashlib
from pathlib import Path

from .analyze import decisions, roles, sections
from .config import SmartEditConfig
from .contracts import load_inputs, validate
from .output import serialize, write_outputs
from .passages import build_passages
from .time_map import rebuild


def smartedit(transcript_path: str | Path, cuts_path: str | Path,
              speechcut_map_path: str | Path, edit_plan_path: str | Path,
              smartedit_map_path: str | Path,
              config: SmartEditConfig | None = None) -> tuple[dict, dict]:
    config = config or SmartEditConfig()
    inputs = [Path(item).resolve(strict=True) for item in
              (transcript_path, cuts_path, speechcut_map_path)]
    outputs = [Path(edit_plan_path).absolute(), Path(smartedit_map_path).absolute()]
    if len(set(inputs + outputs)) != 5:
        raise FileExistsError("All SmartEdit input and output paths must differ")
    transcript, cuts, speech_map, transcript_hash, cuts_hash, speech_map_hash = load_inputs(*inputs)
    passages = build_passages(transcript, speech_map["mappings"])
    edit_decisions = decisions(passages, config)
    auto_removals = [(item["source_start_us"], item["source_end_us"])
                     for item in edit_decisions if item["disposition"] == "AUTO_REMOVE"]
    mappings, duration = rebuild(speech_map["mappings"], auto_removals)
    source = {
        "transcript_path": str(inputs[0]), "transcript_sha256": transcript_hash,
        "cuts_path": str(inputs[1]), "cuts_sha256": cuts_hash,
        "speechcut_time_map_path": str(inputs[2]), "speechcut_time_map_sha256": speech_map_hash,
        "media_path": transcript["source"]["path"], "media_sha256": transcript["source"]["sha256"],
    }
    plan = {
        "schema_version": "1.0.0", "module": {"id": "M3", "version": "1.0.0"},
        "stage": "smartedit", "time_domain": "SOURCE", "source": source,
        "policy": config.to_contract(),
        "passages": [{"id": item.id, "source_start_us": item.source_start_us,
                      "source_end_us": item.source_end_us, "text": item.text,
                      "word_ids": list(item.word_ids), "strength": item.strength}
                     for item in passages],
        "roles": roles(passages), "sections": sections(passages, config),
        "decisions": edit_decisions,
        "summary": {"passage_count": len(passages), "section_count": len(sections(passages, config)),
                    "review_count": sum(item["disposition"] == "REVIEW" for item in edit_decisions),
                    "auto_remove_count": len(auto_removals),
                    "additional_removed_duration_us": speech_map["output_duration_us"] - duration},
        "warnings": ["NO_SPEECH_RECOGNIZED"] if not passages else [],
    }
    plan_hash = hashlib.sha256(serialize(plan)).hexdigest()
    time_map = {
        "schema_version": "1.0.0", "module": {"id": "M3", "version": "1.0.0"},
        "stage": "smartedit", "source_time_domain": "SOURCE", "target_time_domain": "CUT",
        "source": {**source, "edit_plan_sha256": plan_hash},
        "source_start_us": speech_map["source_start_us"],
        "source_end_us": speech_map["source_end_us"],
        "output_duration_us": duration, "mappings": mappings,
    }
    validate(plan, "edit-plan-1.0.0.json")
    validate(time_map, "time-map-smartedit-1.0.0.json")
    write_outputs(outputs[0], outputs[1], plan, time_map)
    return plan, time_map
