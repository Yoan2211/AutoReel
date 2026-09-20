import json

import pytest

from modules.m7_sounddesign.config import SoundDesignConfig
from modules.m7_sounddesign.errors import SoundDesignError
from modules.m7_sounddesign.planner import plan_sounds

from .fixtures import keyframe, make_chain


LOOSE = SoundDesignConfig(minimum_gap_us=1, conflict_window_us=1, maximum_sfx_per_window=20)


def test_visual_appearance_wins_simultaneous_hook_and_zoom(tmp_path):
    paths = make_chain(tmp_path, ["Les ventes progressent de 42 pourcent cette année."],
                       keyframes=[keyframe(0, 1.08)])
    plan = plan_sounds(*paths, config=SoundDesignConfig(minimum_gap_us=1, conflict_window_us=300_000))
    active = [item for item in plan["decisions"] if item["status"] != "NONE"]
    assert len(active) == 1
    assert active[0]["event_kind"] == "VISUAL_APPEARANCE"
    assert active[0]["type"] == "POP"
    assert active[0]["gain_db"] <= -20
    assert {item["event_kind"] for item in plan["decisions"] if item["status"] == "NONE"} == {"HOOK", "ZOOM", "CONCEPT_EMPHASIS"}


def test_broll_uses_subtle_whoosh_and_source_cut_times(tmp_path):
    paths = make_chain(tmp_path, ["Introduction orale sans image particulière.",
                                  "Je marche dans un atelier avec mon téléphone."],
                       mappings=[(0, 1_199_999), (5_000_000, 6_199_999)])
    plan = plan_sounds(*paths, config=LOOSE)
    visual = next(item for item in plan["decisions"] if item["event_kind"] == "VISUAL_APPEARANCE")
    assert visual["type"] == "WHOOSH"
    assert visual["source_time_us"] == 5_000_000
    assert visual["cut_time_us"] == 1_199_999


def test_section_visual_and_transition_conflict_produces_one_sound(tmp_path):
    paths = make_chain(tmp_path, ["Ouverture parlée sans illustration.",
                                  "Les ventes progressent de 42 pourcent."],
                       mappings=[(0, 1_199_999), (5_000_000, 6_199_999)])
    plan = plan_sounds(*paths, config=SoundDesignConfig(minimum_gap_us=1, conflict_window_us=300_000))
    at_change = [item for item in plan["decisions"] if item["cut_time_us"] == 1_199_999]
    assert {item["event_kind"] for item in at_change} == {
        "SECTION_CHANGE", "VISUAL_APPEARANCE", "CONCEPT_EMPHASIS", "TRANSITION"}
    assert sum(item["status"] != "NONE" for item in at_change) == 1
    assert next(item for item in at_change if item["status"] != "NONE")["event_kind"] == "VISUAL_APPEARANCE"


def test_density_suppresses_repeated_sfx_and_records_none(tmp_path):
    paths = make_chain(tmp_path, ["Les ventes montent de 10 pourcent.",
                                  "Les ventes montent de 20 pourcent.",
                                  "Les ventes montent de 30 pourcent."],
                       spacing_us=1_500_000)
    config = SoundDesignConfig(minimum_gap_us=3_000_000, conflict_window_us=1,
                               maximum_sfx_per_window=8)
    plan = plan_sounds(*paths, config=config)
    assert plan["summary"]["none_count"] >= 2
    assert any("density policy" in item["reason"] for item in plan["decisions"] if item["status"] == "NONE")


def test_ambiguous_section_and_zoom_events_are_review(tmp_path):
    paths = make_chain(tmp_path, ["Première idée simplement expliquée.",
                                  "Deuxième thème présenté calmement."],
                       keyframes=[keyframe(0, 1.0), keyframe(5_500_000, 1.04)])
    plan = plan_sounds(*paths, config=LOOSE)
    kinds = {item["event_kind"]: item for item in plan["decisions"]}
    assert kinds["SECTION_CHANGE"]["status"] == "REVIEW"
    assert kinds["ZOOM"]["status"] == "REVIEW"


def test_camera_event_in_deleted_source_range_is_ignored(tmp_path):
    paths = make_chain(tmp_path, ["Ouverture parlée sans illustration.",
                                  "Deuxième thème présenté calmement."],
                       mappings=[(0, 1_199_999), (5_000_000, 6_199_999)],
                       keyframes=[keyframe(3_000_000, 1.08)])
    plan = plan_sounds(*paths, config=LOOSE)
    assert all(item["event_kind"] != "ZOOM" for item in plan["decisions"])


def test_no_speech_produces_empty_plan(tmp_path):
    paths = make_chain(tmp_path, [])
    plan = plan_sounds(*paths)
    assert plan["decisions"] == []
    assert plan["warnings"] == ["NO_SPEECH_RECOGNIZED"]


def test_planning_is_deterministic(tmp_path):
    paths = make_chain(tmp_path, ["Les ventes progressent de 42 pourcent."])
    left = plan_sounds(*paths[:-1], tmp_path / "left.json")
    right = plan_sounds(*paths[:-1], tmp_path / "right.json")
    assert left == right


def test_broken_visual_provenance_is_rejected(tmp_path):
    paths = make_chain(tmp_path, ["Les ventes progressent de 42 pourcent."])
    visual = json.loads(paths[2].read_text(encoding="utf-8"))
    visual["source"]["edit_plan_sha256"] = "f" * 64
    paths[2].write_text(json.dumps(visual), encoding="utf-8")
    with pytest.raises(SoundDesignError, match="visual_plan"):
        plan_sounds(*paths)


def test_existing_output_is_preserved(tmp_path):
    paths = make_chain(tmp_path, ["Les ventes progressent de 42 pourcent."])
    paths[-1].write_text("user data", encoding="utf-8")
    with pytest.raises(FileExistsError):
        plan_sounds(*paths)
    assert paths[-1].read_text(encoding="utf-8") == "user data"
