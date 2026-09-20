import json

import pytest

from modules.m5_visual_planner.config import VisualPlannerConfig
from modules.m5_visual_planner.errors import VisualPlannerError
from modules.m5_visual_planner.planner import plan_visuals

from .fixtures import make_camera, make_inputs


FAST = VisualPlannerConfig(minimum_gap_us=1, minimum_duration_us=500_000)


def test_media_types_are_explainable_and_no_visual_is_explicit(tmp_path):
    sentences = ["Les ventes progressent de 42 pourcent cette année.",
                 "Je marche dans un atelier avec mon téléphone.",
                 "Voici la photo du monument de Paris.",
                 "Imagine le mécanisme de ce processus complexe.",
                 "Cette phrase reste simplement une transition orale."]
    paths = make_inputs(tmp_path, sentences)
    plan = plan_visuals(*paths[:4], config=FAST)
    assert [item["media_type"] for item in plan["requests"]] == [
        "ICON_GRAPHIC", "BROLL", "PHOTO", "ILLUSTRATION", "NONE"]
    assert all(item["reason"] for item in plan["requests"])
    assert plan["summary"]["selected_count"] == 4
    assert plan["requests"][3]["disposition"] == "REVIEW"


def test_density_policy_suppresses_competing_visuals(tmp_path):
    paths = make_inputs(tmp_path, ["Le graphique montre 42 pourcent.", "Le graphique montre 18 pourcent."],
                        section_groups=[[0, 1]], spacing_us=1_500_000)
    plan = plan_visuals(*paths[:4], config=VisualPlannerConfig(minimum_gap_us=3_500_000,
                                                               minimum_duration_us=500_000))
    assert plan["summary"]["selected_count"] == 1
    assert plan["requests"][1]["disposition"] == "NONE"
    assert "density" in plan["requests"][1]["reason"]


def test_section_limit_is_enforced_deterministically(tmp_path):
    paths = make_inputs(tmp_path, ["Imagine ce mécanisme complexe.", "Les ventes atteignent 42 pourcent."],
                        section_groups=[[0, 1]])
    config = VisualPlannerConfig(minimum_gap_us=1, maximum_visuals_per_section=1,
                                 minimum_duration_us=500_000)
    plan = plan_visuals(*paths[:4], config=config)
    assert plan["requests"][0]["disposition"] == "NONE"
    assert plan["requests"][1]["media_type"] == "ICON_GRAPHIC"


def test_source_to_cut_position_uses_only_retained_intersection(tmp_path):
    paths = make_inputs(tmp_path, ["Le graphique explique 42 pourcent de progression."],
                        mappings=[(0, 600_000), (800_000, 1_199_999)])
    plan = plan_visuals(*paths[:4], config=VisualPlannerConfig(minimum_gap_us=1,
                                                               minimum_duration_us=300_000,
                                                               target_duration_us=500_000))
    item = plan["requests"][0]
    assert (item["source_start_us"], item["source_end_us"]) == (0, 500_000)
    assert (item["cut_start_us"], item["cut_end_us"]) == (0, 500_000)


def test_camera_plan_is_optional_but_provenance_is_checked(tmp_path):
    paths = make_inputs(tmp_path, ["Les ventes atteignent 42 pourcent."])
    camera = make_camera(tmp_path / "camera.json", paths[2], paths[6])
    plan = plan_visuals(*paths[:4], camera_plan_path=camera, config=FAST)
    assert plan["source"]["camera_plan_path"] == str(camera.resolve())
    value = json.loads(camera.read_text(encoding="utf-8"))
    value["source"]["smartedit_time_map_sha256"] = "f" * 64
    camera.write_text(json.dumps(value), encoding="utf-8")
    with pytest.raises(VisualPlannerError, match="does not reference"):
        plan_visuals(paths[0], paths[1], paths[2], tmp_path / "other.json", camera, FAST)


def test_planning_is_deterministic(tmp_path):
    paths = make_inputs(tmp_path, ["Les ventes atteignent 42 pourcent."])
    left = plan_visuals(paths[0], paths[1], paths[2], tmp_path / "left.json", config=FAST)
    right = plan_visuals(paths[0], paths[1], paths[2], tmp_path / "right.json", config=FAST)
    assert left == right


def test_no_speech_produces_empty_valid_plan(tmp_path):
    paths = make_inputs(tmp_path, [])
    plan = plan_visuals(*paths[:4])
    assert plan["requests"] == []
    assert plan["warnings"] == ["NO_SPEECH_RECOGNIZED"]


def test_broken_edit_plan_chain_is_rejected(tmp_path):
    paths = make_inputs(tmp_path, ["Les ventes atteignent 42 pourcent."])
    value = json.loads(paths[2].read_text(encoding="utf-8"))
    value["source"]["edit_plan_sha256"] = "f" * 64
    paths[2].write_text(json.dumps(value), encoding="utf-8")
    with pytest.raises(VisualPlannerError, match="edit_plan"):
        plan_visuals(*paths[:4], config=FAST)


def test_existing_output_is_never_overwritten(tmp_path):
    paths = make_inputs(tmp_path, ["Les ventes atteignent 42 pourcent."])
    paths[3].write_text("user data", encoding="utf-8")
    with pytest.raises(FileExistsError):
        plan_visuals(*paths[:4], config=FAST)
    assert paths[3].read_text(encoding="utf-8") == "user data"
