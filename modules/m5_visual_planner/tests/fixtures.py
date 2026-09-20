import hashlib
import json


HASH = "a" * 64


def dump(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return hashlib.sha256(path.read_bytes()).hexdigest()


def make_inputs(root, sentences, *, section_groups=None, spacing_us=5_000_000, mappings=None):
    root.mkdir(parents=True, exist_ok=True)
    segments, passages = [], []
    for index, text in enumerate(sentences):
        start = index * spacing_us
        raw_tokens = text.split()
        step = max(1, 1_200_000 // len(raw_tokens))
        words = []
        for word_index, token in enumerate(raw_tokens):
            word_start = start + word_index * step
            words.append({"id": f"s{index:06d}w{word_index:06d}", "start_us": word_start,
                          "end_us": min(start + 1_200_000, word_start + step - 1),
                          "text": (" " if word_index else "") + token, "probability": .99})
        end = words[-1]["end_us"]
        segments.append({"id": f"s{index:06d}", "start_us": start, "end_us": end,
                         "text": text, "no_speech_probability": .01, "words": words})
        passages.append({"id": f"passage{index:06d}", "source_start_us": start,
                         "source_end_us": end, "text": text,
                         "word_ids": [item["id"] for item in words], "strength": .8})
    duration = max((item["source_end_us"] for item in passages), default=1)
    transcript = {"schema_version": "1.0.0", "module": {"id": "M1", "version": "1.0.0"},
        "time_domain": "SOURCE", "source": {"path": "C:\\media\\source.mov", "sha256": HASH, "manifest_sha256": "b" * 64, "audio_stream_index": 0},
        "analysis": {"origin_us": 0, "duration_us": duration, "sample_rate_hz": 16000, "channels": 1},
        "engine": {"name": "fixture", "version": "1", "model": "fixture", "device": "cpu", "compute_type": "int8"},
        "options": {"language_requested": "fr", "beam_size": 5, "word_timestamps": True, "vad_filter": False, "condition_on_previous_text": False, "task": "transcribe"},
        "language": "fr", "language_probability": 1.0,
        "status": "transcribed" if sentences else "no_speech_recognized",
        "text": " ".join(sentences), "segments": segments,
        "warnings": [] if sentences else ["NO_SPEECH_RECOGNIZED"]}
    transcript_path = root / "transcript.json"
    transcript_hash = dump(transcript_path, transcript)
    if section_groups is None:
        section_groups = [[index] for index in range(len(passages))]
    sections = []
    for index, group in enumerate(section_groups):
        selected = [passages[item] for item in group]
        sections.append({"id": f"section{index:06d}", "title": "thème",
                         "theme_terms": ["exemple"], "passage_ids": [item["id"] for item in selected],
                         "source_start_us": selected[0]["source_start_us"],
                         "source_end_us": selected[-1]["source_end_us"]})
    source = {"transcript_path": str(transcript_path.resolve()), "transcript_sha256": transcript_hash,
              "cuts_path": "cuts.json", "cuts_sha256": "c" * 64,
              "speechcut_time_map_path": "speech-map.json", "speechcut_time_map_sha256": "d" * 64,
              "media_path": transcript["source"]["path"], "media_sha256": HASH}
    edit = {"schema_version": "1.0.0", "module": {"id": "M3", "version": "1.0.0"},
            "stage": "smartedit", "time_domain": "SOURCE", "source": source,
            "policy": {"semantic_similarity_threshold": .72, "topic_similarity_threshold": .18,
                       "max_section_sentences": 4, "weak_formulation_margin": .15,
                       "auto_remove_exact_duplicates": False},
            "passages": passages,
            "roles": ([{"role": "HOOK", "passage_id": passages[0]["id"], "confidence": "MEDIUM", "reason": "fixture"}] if passages else []),
            "sections": sections, "decisions": [],
            "summary": {"passage_count": len(passages), "section_count": len(sections), "review_count": 0,
                        "auto_remove_count": 0, "additional_removed_duration_us": 0},
            "warnings": [] if passages else ["NO_SPEECH_RECOGNIZED"]}
    edit_path = root / "edit-plan.json"
    edit_hash = dump(edit_path, edit)
    if mappings is None:
        mappings = [] if not passages else [(0, duration)]
    raw_mappings, cut_cursor = [], 0
    for index, (start, end) in enumerate(mappings):
        raw_mappings.append({"id": f"map{index:06d}",
                             "source": {"time_domain": "SOURCE", "start_us": start, "end_us": end},
                             "target": {"time_domain": "CUT", "start_us": cut_cursor, "end_us": cut_cursor + end - start}})
        cut_cursor += end - start
    time_map = {"schema_version": "1.0.0", "module": {"id": "M3", "version": "1.0.0"},
                "stage": "smartedit", "source_time_domain": "SOURCE", "target_time_domain": "CUT",
                "source": {**source, "edit_plan_sha256": edit_hash}, "source_start_us": 0,
                "source_end_us": duration, "output_duration_us": cut_cursor, "mappings": raw_mappings}
    map_path = root / "time-map.json"
    map_hash = dump(map_path, time_map)
    return edit_path, transcript_path, map_path, root / "visual-plan.json", edit, time_map, map_hash


def make_camera(path, map_path, map_hash):
    value = {"schema_version": "1.0.0", "module": {"id": "M4", "version": "1.0.0"},
             "stage": "autocam", "time_domain": "SOURCE",
             "source": {"manifest_path": "source.json", "manifest_sha256": "b" * 64,
                        "smartedit_time_map_path": str(map_path.resolve()), "smartedit_time_map_sha256": map_hash,
                        "media_path": "C:\\media\\source.mov", "media_sha256": HASH},
             "output": {"width": 1080, "height": 1920, "aspect_ratio": "9:16"},
             "input_geometry": {"encoded_width": 1920, "encoded_height": 1080, "display_width": 1920, "display_height": 1080, "rotation_degrees": 0},
             "engine": {"detector": "fixture", "detector_version": "1", "device": "cpu", "frame_provider": "fixture"},
             "policy": {"sample_interval_us": 250000, "output_width": 1080, "output_height": 1920, "device": "cpu", "cpu_fallback": True, "smoothing_alpha": .22, "lost_hold_us": 1000000, "keyframe_interval_us": 2000000, "center_change_threshold": .025, "zoom_change_threshold": .012, "natural_zoom_max": 1.08, "hard_zoom_max": 1.15, "headroom_ratio": .12},
             "shots": [], "summary": {"source_interval_count": 0, "frames_analyzed": 0, "detections": 0, "keyframes": 0}, "warnings": []}
    dump(path, value)
    return path
