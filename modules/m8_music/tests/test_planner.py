import json

import pytest

from modules.m8_music.config import MusicPlannerConfig
from modules.m8_music.errors import MusicPlannerError
from modules.m8_music.planner import plan_music

from .fixtures import make_music_chain, move_first_active_sfx


LONG_SPEECH = ["Les ventes et la stratégie client progressent.",
               "Cette explication reste claire pour la voix.",
               "Le marché confirme la stratégie de l'entreprise."]


def test_long_thematic_program_gets_one_stable_music_region(tmp_path):
    paths = make_music_chain(tmp_path, LONG_SPEECH, spacing_us=8_000_000)
    plan = plan_music(*paths)
    assert plan["decision"] == {"status": "MUSIC", "mood": "clean_modern_business",
                                "energy": "LOW", "confidence": "HIGH",
                                "reason": "A stable low-level music bed can support rhythm without following micro-events"}
    assert len(plan["regions"]) == 1
    assert plan["regions"][0]["strategy"] == "STABLE_BED"
    assert plan["regions"][0]["speech_gain_db"] == -28
    assert plan["regions"][0]["no_speech_gain_db"] == -21
    assert "track" not in plan["asset_request"] and "path" not in plan["asset_request"]


def test_short_program_explicitly_selects_none(tmp_path):
    paths = make_music_chain(tmp_path, ["Une phrase très courte suffit ici."])
    plan = plan_music(*paths)
    assert plan["decision"]["status"] == "NONE"
    assert plan["asset_request"] is None
    assert plan["regions"] == [] and plan["level_regions"] == []
    assert plan["warnings"] == ["MUSIC_NOT_RECOMMENDED"]


def test_ambiguous_neutral_context_stays_review(tmp_path):
    sentences = ["Une phrase simplement formulée.", "Une autre idée calmement présentée.",
                 "La conclusion reste volontairement sobre."]
    paths = make_music_chain(tmp_path, sentences, spacing_us=8_000_000)
    plan = plan_music(*paths)
    assert plan["decision"]["status"] == "REVIEW"
    assert plan["decision"]["mood"] == "clean_modern_neutral"


def test_voice_is_ducked_and_long_silence_can_lift(tmp_path):
    paths = make_music_chain(tmp_path, LONG_SPEECH, spacing_us=8_000_000)
    plan = plan_music(*paths)
    speech = [item for item in plan["level_regions"] if item["mode"] == "SPEECH_DUCK"]
    lifts = [item for item in plan["level_regions"] if item["mode"] == "NO_SPEECH_LIFT"]
    assert speech and lifts
    assert all(item["gain_db"] == -28 for item in speech)
    assert all(item["gain_db"] == -21 for item in lifts)


def test_music_lift_is_blocked_around_active_sfx(tmp_path):
    paths = make_music_chain(tmp_path, LONG_SPEECH, spacing_us=8_000_000)
    move_first_active_sfx(paths[4], 4_000_000)
    plan = plan_music(*paths)
    protected = [item for item in plan["level_regions"] if item["mode"] == "SFX_PROTECTED"]
    assert protected
    assert any(item["cut_start_us"] <= 4_000_000 < item["cut_end_us"] for item in protected)
    assert all(item["gain_db"] == -28 for item in protected)


def test_short_pauses_keep_stable_level_instead_of_pumping(tmp_path):
    paths = make_music_chain(tmp_path, LONG_SPEECH, spacing_us=1_400_000)
    config = MusicPlannerConfig(minimum_music_duration_us=1_000_000,
                                proposal_duration_us=2_000_000,
                                speech_merge_gap_us=50_000)
    plan = plan_music(*paths, config=config)
    assert any(item["mode"] == "STABLE_BASE" for item in plan["level_regions"])
    assert not any(item["mode"] == "NO_SPEECH_LIFT" for item in plan["level_regions"])


def test_source_intervals_preserve_discontinuous_mapping(tmp_path):
    paths = make_music_chain(tmp_path, LONG_SPEECH, spacing_us=8_000_000,
                             mappings=[(0, 1_199_999), (8_000_000, 9_199_999),
                                       (16_000_000, 17_199_999)])
    config = MusicPlannerConfig(minimum_music_duration_us=1_000_000,
                                proposal_duration_us=2_000_000)
    plan = plan_music(*paths, config=config)
    assert len(plan["regions"][0]["source_intervals"]) == 3
    assert plan["regions"][0]["cut_end_us"] == 3_599_997


def test_fades_are_capped_for_short_review_region(tmp_path):
    paths = make_music_chain(tmp_path, ["Une première phrase sobre.",
                                       "Une deuxième phrase sobre."], spacing_us=1_500_000)
    config = MusicPlannerConfig(minimum_music_duration_us=1_000_000,
                                proposal_duration_us=10_000_000,
                                fade_in_us=5_000_000, fade_out_us=5_000_000)
    plan = plan_music(*paths, config=config)
    region = plan["regions"][0]
    assert region["fade_in_us"] <= (region["cut_end_us"] - region["cut_start_us"]) // 2
    assert region["fade_out_us"] <= (region["cut_end_us"] - region["cut_start_us"]) // 2


def test_no_speech_selects_none(tmp_path):
    paths = make_music_chain(tmp_path, [])
    plan = plan_music(*paths)
    assert plan["decision"]["status"] == "NONE"


def test_broken_sound_provenance_is_rejected(tmp_path):
    paths = make_music_chain(tmp_path, LONG_SPEECH, spacing_us=8_000_000)
    sound = json.loads(paths[4].read_text(encoding="utf-8"))
    sound["source"]["visual_plan_sha256"] = "f" * 64
    paths[4].write_text(json.dumps(sound), encoding="utf-8")
    with pytest.raises(MusicPlannerError, match="sound_plan"):
        plan_music(*paths)


def test_planning_is_deterministic(tmp_path):
    paths = make_music_chain(tmp_path, LONG_SPEECH, spacing_us=8_000_000)
    left = plan_music(*paths[:-1], tmp_path / "left.json")
    right = plan_music(*paths[:-1], tmp_path / "right.json")
    assert left == right


def test_existing_output_is_preserved(tmp_path):
    paths = make_music_chain(tmp_path, LONG_SPEECH, spacing_us=8_000_000)
    paths[-1].write_text("user data", encoding="utf-8")
    with pytest.raises(FileExistsError):
        plan_music(*paths)
    assert paths[-1].read_text(encoding="utf-8") == "user data"
