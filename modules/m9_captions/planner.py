from pathlib import Path

from .config import CaptionsConfig
from .contracts import load_inputs, validate_captions
from .output import write_exclusive
from .projection import project_words, source_intervals_for_range, validate_v1
from .segmentation import segment, text_and_lines


def _caption(index, words, v1, transcript_hash, config):
    text, lines = text_and_lines(words, config.maximum_characters_per_line)
    start, end = words[0].timeline_start_us, words[-1].timeline_end_us
    intervals = source_intervals_for_range(start, end, v1)
    return {"id": f"caption{index:06d}", "text": text, "lines": lines,
            "word_ids": [word.id for word in words],
            "words": [{"id": word.id, "text": word.text,
                       "source_start_us": word.source_start_us, "source_end_us": word.source_end_us,
                       "cut_start_us": word.cut_start_us, "cut_end_us": word.cut_end_us,
                       "timeline_start_us": word.timeline_start_us,
                       "timeline_end_us": word.timeline_end_us} for word in words],
            "source_start_us": intervals[0]["source_start_us"],
            "source_end_us": intervals[-1]["source_end_us"], "source_intervals": intervals,
            "cut_start_us": words[0].cut_start_us, "cut_end_us": words[-1].cut_end_us,
            "timeline_start_us": start, "timeline_end_us": end,
            "provenance": {"transcript_sha256": transcript_hash,
                           "segment_ids": list(dict.fromkeys(word.segment_id for word in words))}}


def plan_captions(transcript_path, timeline_draft_path, captions_path, config=None):
    config = config or CaptionsConfig()
    output = Path(captions_path).absolute()
    transcript, timeline, transcript_hash, timeline_hash, transcript_path, timeline_path = load_inputs(
        transcript_path, timeline_draft_path)
    if output in {transcript_path, timeline_path} or output.exists() or output.is_symlink():
        raise FileExistsError(f"Captions output must be a new file: {output}")
    v1 = next(item for item in timeline["tracks"] if item["id"] == "V1")["events"]
    validate_v1(v1, timeline["format"]["duration_us"])
    words = project_words(transcript, v1)
    groups = segment(words, config)
    captions = [_caption(index, group, v1, transcript_hash, config)
                for index, group in enumerate(groups)]
    value = {"schema_version": "1.0.0", "module": {"id": "M9", "version": "1.0.0"},
             "stage": "captions", "time_domains": {"source": "SOURCE", "cut": "CUT", "timeline": "TIMELINE"},
             "source": {"transcript_path": str(transcript_path), "transcript_sha256": transcript_hash,
                        "timeline_draft_path": str(timeline_path), "timeline_draft_sha256": timeline_hash},
             "policy": config.to_contract(),
             "style": {"position": "LOWER_SAFE", "vertical_position_ratio": 0.78,
                       "alignment": "CENTER", "preset": "MODERN_READABLE",
                       "maximum_lines": 2, "word_highlight": True,
                       "animation": "SUBTLE_OR_NONE"},
             "captions": captions,
             "summary": {"caption_count": len(captions), "included_word_count": len(words),
                         "excluded_word_count": sum(len(s["words"]) for s in transcript["segments"]) - len(words)},
             "warnings": (["NO_CAPTIONS"] if not captions else [])}
    validate_captions(value)
    write_exclusive(output, value)
    return value
