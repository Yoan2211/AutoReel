"""M2 orchestration: transcript JSON to decisions and a speechcut time map."""

import hashlib
import json
from pathlib import Path

from .analyze import analyze
from .config import SpeechCutConfig
from .contracts import load_transcript, validate
from .errors import SpeechCutError
from .output import write_outputs
from .resolve import select_auto
from .time_map import build_time_map


def _decision(index: int, candidate, suppressed: bool) -> dict:
    disposition = "SUPPRESSED" if suppressed else candidate.disposition
    result = {
        "id": f"cut{index:06d}", "kind": candidate.kind,
        "disposition": disposition, "confidence": candidate.confidence,
        "time_domain": "SOURCE", "start_us": candidate.start_us,
        "end_us": candidate.end_us, "duration_us": candidate.duration_us,
        "reason": candidate.reason, "word_ids": list(candidate.word_ids),
    }
    if candidate.retained_pause_us is not None:
        result["retained_pause_us"] = candidate.retained_pause_us
    return result


def speechcut(transcript_path: str | Path, cuts_path: str | Path,
              time_map_path: str | Path, config: SpeechCutConfig | None = None) -> tuple[dict, dict]:
    config = config or SpeechCutConfig()
    source_path = Path(transcript_path).resolve(strict=True)
    cuts_destination = Path(cuts_path).absolute()
    map_destination = Path(time_map_path).absolute()
    if len({source_path, cuts_destination, map_destination}) != 3:
        raise FileExistsError("Input and output paths must all differ")
    transcript, transcript_hash = load_transcript(source_path)
    words, candidates = analyze(transcript, config)
    applied, suppressed = select_auto(candidates)
    analysis_start = transcript["analysis"]["origin_us"]
    analysis_end = analysis_start + transcript["analysis"]["duration_us"]
    if words and (words[0].start_us < analysis_start or words[-1].end_us > analysis_end):
        raise SpeechCutError("Transcript words lie outside declared analysis bounds")
    mappings, output_duration = build_time_map(analysis_start, analysis_end, applied)
    decisions = [_decision(index, candidate, index in suppressed)
                 for index, candidate in enumerate(candidates)]
    common_source = {
        "transcript_path": str(source_path), "transcript_sha256": transcript_hash,
        "media_path": transcript["source"]["path"], "media_sha256": transcript["source"]["sha256"],
    }
    cuts = {
        "schema_version": "1.0.0", "module": {"id": "M2", "version": "1.0.0"},
        "stage": "speechcut", "time_domain": "SOURCE", "source": common_source,
        "policy": config.to_contract(), "decisions": decisions,
        "summary": {
            "candidate_count": len(decisions),
            "auto_applied_count": len(applied),
            "review_count": sum(item["disposition"] == "REVIEW" for item in decisions),
            "suppressed_count": len(suppressed),
            "removed_duration_us": sum(item.duration_us for item in applied),
        },
        "warnings": (["NO_SPEECH_RECOGNIZED"] if transcript["status"] == "no_speech_recognized" else []),
    }
    cuts_hash = hashlib.sha256((json.dumps(cuts, ensure_ascii=False, indent=2, allow_nan=False) + "\n").encode("utf-8")).hexdigest()
    time_map = {
        "schema_version": "1.0.0", "module": {"id": "M2", "version": "1.0.0"},
        "stage": "speechcut", "source_time_domain": "SOURCE", "target_time_domain": "CUT",
        "source": {**common_source, "cuts_sha256": cuts_hash},
        "source_start_us": analysis_start, "source_end_us": analysis_end,
        "output_duration_us": output_duration, "mappings": mappings,
    }
    validate(cuts, "cuts-1.0.0.json")
    validate(time_map, "time-map-speechcut-1.0.0.json")
    write_outputs(cuts_destination, map_destination, cuts, time_map)
    return cuts, time_map
