import hashlib
import json

import pytest

from modules.m10_timeline_compiler.compiler import compile_pass_a
from modules.m10_timeline_compiler.tests.fixtures import dump, load, make_compiler_inputs, rebind
from modules.m9_captions.contracts import CaptionsError
from modules.m9_captions.planner import plan_captions
from modules.m9_captions.projection import ProjectedWord, project_words, source_intervals_for_range
from modules.m9_captions.segmentation import segment
from modules.m9_captions.config import CaptionsConfig


def make_chain(tmp_path):
    paths, timeline_path = make_compiler_inputs(tmp_path)
    edit = load(paths[2]); transcript_path = __import__("pathlib").Path(edit["source"]["transcript_path"])
    transcript = load(transcript_path)
    media = load(paths[0])["source"]
    transcript["source"].update(path=media["path"], sha256=media["sha256"])
    transcript_hash = dump(transcript_path, transcript)
    edit["source"]["transcript_sha256"] = transcript_hash
    dump(paths[2], edit)
    rebind(paths)
    compile_pass_a(*paths, timeline_path)
    return transcript_path, timeline_path, tmp_path / "captions.json"


def test_end_to_end_preserves_words_domains_style_and_input(tmp_path):
    transcript, timeline, output = make_chain(tmp_path)
    timeline_hash = hashlib.sha256(timeline.read_bytes()).hexdigest()
    value = plan_captions(transcript, timeline, output)
    assert value["captions"] and all(1 <= len(item["words"]) <= 6 for item in value["captions"])
    assert all(len(item["lines"]) <= 2 for item in value["captions"])
    assert all(len(line) <= value["policy"]["maximum_characters_per_line"]
               for item in value["captions"] for line in item["lines"])
    assert all(item["cut_start_us"] == item["timeline_start_us"] for item in value["captions"])
    assert all(item["text"] == "".join(word["text"] for word in item["words"]).strip()
               for item in value["captions"])
    assert value["style"]["word_highlight"] is True
    assert hashlib.sha256(timeline.read_bytes()).hexdigest() == timeline_hash


def test_deleted_words_never_project_and_cross_cut_keeps_source_intervals():
    transcript = {"segments": [{"id": "s000000", "words": [
        {"id": "s000000w000000", "text": "Un", "start_us": 100, "end_us": 200},
        {"id": "s000000w000001", "text": " supprimé", "start_us": 300, "end_us": 400},
        {"id": "s000000w000002", "text": " retour", "start_us": 1000, "end_us": 1100}]}]}
    v1 = [{"source_start_us": 0, "source_end_us": 250, "cut_start_us": 0, "cut_end_us": 250,
           "timeline_start_us": 0, "timeline_end_us": 250},
          {"source_start_us": 1000, "source_end_us": 1200, "cut_start_us": 250, "cut_end_us": 450,
           "timeline_start_us": 250, "timeline_end_us": 450}]
    words = project_words(transcript, v1)
    assert [item.id for item in words] == ["s000000w000000", "s000000w000002"]
    assert source_intervals_for_range(100, 350, v1) == [
        {"source_start_us": 100, "source_end_us": 250},
        {"source_start_us": 1000, "source_end_us": 1100}]


def test_segmentation_breaks_on_punctuation_and_avoids_small_orphan():
    def word(index, text, start):
        return ProjectedWord(str(index), "s", text, start, start + 100, start, start + 100, start, start + 100)
    words = [word(0, "Bonjour", 0), word(1, " à", 120), word(2, " tous.", 240),
             word(3, " Et", 900_000), word(4, " bienvenue", 900_120)]
    groups = segment(words, CaptionsConfig())
    assert [len(item) for item in groups] == [3, 2]


def test_transcript_not_referenced_by_timeline_is_rejected(tmp_path):
    transcript, timeline, output = make_chain(tmp_path)
    value = load(transcript); value["text"] += " altéré"
    transcript.write_text(json.dumps(value), encoding="utf-8")
    with pytest.raises(CaptionsError, match="does not reference"):
        plan_captions(transcript, timeline, output)


def test_existing_output_is_preserved(tmp_path):
    transcript, timeline, output = make_chain(tmp_path)
    output.write_text("travail utilisateur", encoding="utf-8")
    with pytest.raises(FileExistsError):
        plan_captions(transcript, timeline, output)
    assert output.read_text(encoding="utf-8") == "travail utilisateur"
