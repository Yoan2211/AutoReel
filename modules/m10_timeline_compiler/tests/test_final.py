import hashlib
import json

import pytest

from modules.m9_captions.planner import plan_captions
from modules.m9_captions.tests.test_captions import make_chain
from modules.m10_timeline_compiler.errors import TimelineCompilerError
from modules.m10_timeline_compiler.final_compiler import compile_final


def final_inputs(tmp_path):
    transcript, draft, captions = make_chain(tmp_path)
    plan_captions(transcript, draft, captions)
    return draft, captions, tmp_path / "timeline.json"


def test_final_preserves_pass_a_and_materializes_v3_exactly(tmp_path):
    draft_path, captions_path, output = final_inputs(tmp_path)
    draft_bytes = draft_path.read_bytes()
    draft = json.loads(draft_bytes)
    captions = json.loads(captions_path.read_text(encoding="utf-8"))
    value = compile_final(draft_path, captions_path, output)
    final_tracks = {item["id"]: item for item in value["tracks"]}
    draft_tracks = {item["id"]: item for item in draft["tracks"]}
    assert all(final_tracks[key] == draft_tracks[key] for key in ("V1", "V2", "A1", "A2", "A3"))
    assert len(final_tracks["V3"]["events"]) == len(captions["captions"])
    first, planned = final_tracks["V3"]["events"][0], captions["captions"][0]
    for key in ("text", "lines", "source_start_us", "source_end_us", "source_intervals",
                "cut_start_us", "cut_end_us", "timeline_start_us", "timeline_end_us", "words"):
        assert first[key] == planned[key]
    assert first["style"] == captions["style"] and first["provenance"]["module"]["id"] == "M9"
    assert draft_path.read_bytes() == draft_bytes


def test_wrong_timeline_draft_provenance_is_rejected(tmp_path):
    draft, captions, output = final_inputs(tmp_path)
    value = json.loads(captions.read_text(encoding="utf-8"))
    value["source"]["timeline_draft_sha256"] = "f" * 64
    captions.write_text(json.dumps(value), encoding="utf-8")
    with pytest.raises(TimelineCompilerError, match="does not reference exactly"):
        compile_final(draft, captions, output)


@pytest.mark.parametrize("mutation,message", [
    ("outside", "outside timeline duration"),
    ("overlap", "overlap"),
    ("domain", "CUT/TIMELINE"),
])
def test_invalid_caption_timing_is_rejected(tmp_path, mutation, message):
    draft, captions, output = final_inputs(tmp_path)
    value = json.loads(captions.read_text(encoding="utf-8"))
    if mutation == "outside":
        value["captions"][-1]["timeline_end_us"] = json.loads(draft.read_text(encoding="utf-8"))["format"]["duration_us"] + 1
        value["captions"][-1]["cut_end_us"] = value["captions"][-1]["timeline_end_us"]
    elif mutation == "overlap":
        value["captions"][1]["timeline_start_us"] = value["captions"][0]["timeline_end_us"] - 1
        value["captions"][1]["cut_start_us"] = value["captions"][1]["timeline_start_us"]
    else:
        value["captions"][0]["cut_start_us"] += 1
    captions.write_text(json.dumps(value), encoding="utf-8")
    with pytest.raises(TimelineCompilerError, match=message):
        compile_final(draft, captions, output)


def test_final_output_is_exclusive(tmp_path):
    draft, captions, output = final_inputs(tmp_path)
    output.write_text("travail utilisateur", encoding="utf-8")
    with pytest.raises(FileExistsError):
        compile_final(draft, captions, output)
    assert output.read_text(encoding="utf-8") == "travail utilisateur"
