import hashlib
import json
from pathlib import Path


def make_inputs(root: Path, sentences: list[str], *, gap: int = 100_000):
    words, segments, cursor, word_index = [], [], 0, 0
    for segment_index, sentence in enumerate(sentences):
        segment_words = []
        for token in sentence.split():
            text = " " + token
            item = {"id": f"s{segment_index:06d}w{word_index:06d}", "start_us": cursor,
                    "end_us": cursor + 100_000, "text": text, "probability": 0.99}
            segment_words.append(item); words.append(item); word_index += 1; cursor += 120_000
        segments.append({"id": f"s{segment_index:06d}", "start_us": segment_words[0]["start_us"],
                         "end_us": segment_words[-1]["end_us"], "text": "".join(w["text"] for w in segment_words),
                         "no_speech_probability": 0.01, "words": segment_words})
        cursor += gap
    duration = max(cursor, 1)
    transcript = {"schema_version": "1.0.0", "module": {"id": "M1", "version": "1.0.0"},
      "time_domain": "SOURCE", "source": {"path": "C:\\media\\source.mov", "sha256": "a"*64, "manifest_sha256": "b"*64, "audio_stream_index": 1},
      "analysis": {"origin_us": 0, "duration_us": duration, "sample_rate_hz": 16000, "channels": 1},
      "engine": {"name": "fixture", "version": "1", "model": "fixture", "device": "cpu", "compute_type": "int8"},
      "options": {"language_requested": "fr", "beam_size": 5, "word_timestamps": True, "vad_filter": False, "condition_on_previous_text": False, "task": "transcribe"},
      "language": "fr", "language_probability": 1.0, "status": "transcribed", "text": " ".join(sentences), "segments": segments, "warnings": []}
    transcript_path = root / "transcript.json"; _write(transcript_path, transcript)
    transcript_hash = _hash(transcript_path)
    source = {"transcript_path": str(transcript_path.resolve()), "transcript_sha256": transcript_hash,
              "media_path": transcript["source"]["path"], "media_sha256": "a"*64}
    cuts = {"schema_version": "1.0.0", "module": {"id": "M2", "version": "1.0.0"}, "stage": "speechcut", "time_domain": "SOURCE", "source": source,
      "policy": {"long_silence_us": 1200000, "review_pause_us": 850000, "retained_pause_us": 420000, "filler_padding_us": 35000, "filler_max_duration_us": 900000, "repetition_max_gap_us": 450000, "phrase_restart_max_gap_us": 900000, "phrase_restart_min_words": 2, "phrase_restart_max_words": 6, "false_start_max_words": 4, "auto_apply_fillers": True, "auto_apply_repetitions": True},
      "decisions": [], "summary": {"candidate_count": 0, "auto_applied_count": 0, "review_count": 0, "suppressed_count": 0, "removed_duration_us": 0}, "warnings": []}
    cuts_path = root / "cuts.json"; _write(cuts_path, cuts); cuts_hash = _hash(cuts_path)
    time_map = {"schema_version": "1.0.0", "module": {"id": "M2", "version": "1.0.0"}, "stage": "speechcut", "source_time_domain": "SOURCE", "target_time_domain": "CUT", "source": {**source, "cuts_sha256": cuts_hash}, "source_start_us": 0, "source_end_us": duration, "output_duration_us": duration, "mappings": [{"id": "map000000", "source": {"time_domain": "SOURCE", "start_us": 0, "end_us": duration}, "target": {"time_domain": "CUT", "start_us": 0, "end_us": duration}}]}
    map_path = root / "speechcut-map.json"; _write(map_path, time_map)
    return transcript_path, cuts_path, map_path, transcript


def _write(path, value): path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
def _hash(path): return hashlib.sha256(path.read_bytes()).hexdigest()
