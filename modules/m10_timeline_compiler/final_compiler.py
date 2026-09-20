from copy import deepcopy
from pathlib import Path

from .errors import TimelineCompilerError
from .final_contracts import load_final_inputs, verify_unchanged
from .final_validation import validate_caption_inputs, validate_final
from .output import write_exclusive


def _caption_event(index, caption, style, captions_hash):
    return {"id": f"v3_{index:06d}", "type": "CAPTION", "caption_id": caption["id"],
            "text": caption["text"], "lines": deepcopy(caption["lines"]),
            "source_start_us": caption["source_start_us"], "source_end_us": caption["source_end_us"],
            "source_intervals": deepcopy(caption["source_intervals"]),
            "cut_start_us": caption["cut_start_us"], "cut_end_us": caption["cut_end_us"],
            "timeline_start_us": caption["timeline_start_us"], "timeline_end_us": caption["timeline_end_us"],
            "word_ids": deepcopy(caption["word_ids"]), "words": deepcopy(caption["words"]),
            "style": deepcopy(style),
            "provenance": {"module": {"id": "M9", "version": "1.0.0"},
                           "captions_sha256": captions_hash,
                           "transcript_sha256": caption["provenance"]["transcript_sha256"],
                           "segment_ids": deepcopy(caption["provenance"]["segment_ids"])}}


def compile_final(timeline_draft_path, captions_path, timeline_path):
    output = Path(timeline_path).absolute()
    draft, captions, draft_hash, captions_hash, draft_path, captions_path, draft_signature, captions_signature = load_final_inputs(
        timeline_draft_path, captions_path)
    if output in {draft_path, captions_path} or output.exists() or output.is_symlink():
        raise FileExistsError(f"Final timeline must be a new file: {output}")
    draft_v1 = next(item for item in draft["tracks"] if item["id"] == "V1")["events"]
    validate_caption_inputs(captions, draft["format"]["duration_us"], draft_v1)
    tracks = deepcopy(draft["tracks"])
    v3 = next(item for item in tracks if item["id"] == "V3")
    if v3["events"]:
        raise TimelineCompilerError("Pass A V3 must be empty before final compilation")
    v3["events"] = [_caption_event(index, caption, captions["style"], captions_hash)
                    for index, caption in enumerate(captions["captions"])]
    value = {"schema_version": "1.0.0", "module": {"id": "M10", "version": "1.0.0"},
             "stage": "timeline_compiler_final", "time_domains": deepcopy(draft["time_domains"]),
             "source": {"timeline_draft_path": str(draft_path), "timeline_draft_sha256": draft_hash,
                        "captions_path": str(captions_path), "captions_sha256": captions_hash,
                        "pass_a_source": deepcopy(draft["source"])},
             "format": deepcopy(draft["format"]), "tracks": tracks,
             "unmaterialized": deepcopy(draft["unmaterialized"]),
             "diagnostics": deepcopy(draft["diagnostics"]),
             "summary": {"track_count": 6,
                         "event_count": sum(len(item["events"]) for item in tracks),
                         "caption_event_count": len(v3["events"]),
                         "pass_a_event_count": draft["summary"]["event_count"],
                         "unmaterialized_count": len(draft["unmaterialized"]),
                         "diagnostic_count": len(draft["diagnostics"])}}
    validate_final(value, draft, captions)
    verify_unchanged(draft_path, draft_signature, draft_hash, "timeline_draft.json")
    verify_unchanged(captions_path, captions_signature, captions_hash, "captions.json")
    write_exclusive(output, value)
    return value
