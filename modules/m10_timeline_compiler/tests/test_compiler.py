import json

import pytest

from modules.m10_timeline_compiler.compiler import compile_pass_a
from modules.m10_timeline_compiler.errors import TimelineCompilerError

from .fixtures import load, make_compiler_inputs


def compile_fixture(tmp_path, **kwargs):
    paths, output = make_compiler_inputs(tmp_path, **kwargs)
    return paths, output, compile_pass_a(*paths, output)


def tracks(value):
    return {item["id"]: item for item in value["tracks"]}


def test_pass_a_compiles_six_fixed_tracks_and_schema(tmp_path):
    paths, output, draft = compile_fixture(tmp_path)
    assert output.is_file()
    assert [item["id"] for item in draft["tracks"]] == ["V1", "V2", "V3", "A1", "A2", "A3"]
    assert tracks(draft)["V3"]["events"] == []
    assert draft["stage"] == "timeline_compiler_pass_a"


def test_v1_and_a1_are_rebuilt_only_from_m3_segments(tmp_path):
    _, _, draft = compile_fixture(tmp_path)
    v1, a1 = tracks(draft)["V1"]["events"], tracks(draft)["A1"]["events"]
    assert [(x["source_start_us"], x["source_end_us"]) for x in v1] == [(0, 7_000_000), (8_000_000, 17_200_000)]
    assert [(x["cut_start_us"], x["cut_end_us"]) for x in v1] == [(0, 7_000_000), (7_000_000, 16_200_000)]
    assert [(x["timeline_start_us"], x["timeline_end_us"]) for x in a1] == [(0, 7_000_000), (7_000_000, 16_200_000)]


def test_camera_is_attached_as_v1_keyframes_not_media(tmp_path):
    _, _, draft = compile_fixture(tmp_path)
    v1 = tracks(draft)["V1"]["events"]
    assert all(item["camera_keyframes"] for item in v1)
    assert v1[1]["camera_keyframes"][0]["source_us"] == 8_000_000
    assert v1[1]["camera_keyframes"][0]["cut_us"] == 7_000_000
    assert all(event["type"] != "CAMERA" for track in draft["tracks"] for event in track["events"])


def test_only_resolved_requests_are_materialized_and_others_remain_diagnostics(tmp_path):
    _, _, draft = compile_fixture(tmp_path)
    materialized = [event for track in draft["tracks"] if track["id"] in {"V2", "A2", "A3"} for event in track["events"]]
    assert materialized
    assert all(event["asset_id"] for event in materialized)
    assert all(item["status"] in {"REVIEW", "UNRESOLVED"} for item in draft["unmaterialized"])


def test_music_preserves_source_cut_timeline_levels_and_ducking(tmp_path):
    _, _, draft = compile_fixture(tmp_path)
    music = tracks(draft)["A2"]["events"][0]
    assert music["source_intervals"]
    assert music["cut_start_us"] == music["timeline_start_us"] == 0
    assert music["level_regions"]
    assert all({"source_intervals", "cut_start_us", "timeline_start_us", "gain_db"} <= set(item) for item in music["level_regions"])


def test_sfx_preserves_point_coordinates_and_asset_duration(tmp_path):
    _, _, draft = compile_fixture(tmp_path)
    sfx = tracks(draft)["A3"]["events"]
    assert all(item["cut_time_us"] == item["timeline_start_us"] for item in sfx)
    assert all(item["timeline_end_us"] > item["timeline_start_us"] for item in sfx)


def test_output_is_exclusive(tmp_path):
    paths, output = make_compiler_inputs(tmp_path)
    output.write_text("user work", encoding="utf-8")
    with pytest.raises(FileExistsError):
        compile_pass_a(*paths, output)
    assert output.read_text(encoding="utf-8") == "user work"


def test_broken_provenance_is_rejected(tmp_path):
    paths, output = make_compiler_inputs(tmp_path)
    assets = load(paths[-1]); assets["source"]["music_plan_sha256"] = "f" * 64
    paths[-1].write_text(json.dumps(assets), encoding="utf-8")
    with pytest.raises(TimelineCompilerError, match="provenance"):
        compile_pass_a(*paths, output)


def test_missing_resolved_asset_is_rejected(tmp_path):
    paths, output = make_compiler_inputs(tmp_path)
    manifest = load(paths[-1])
    asset = next(item for item in manifest["assets"] if item["request_ids"])
    asset_path = tmp_path / asset["path"]
    asset_path.unlink()
    with pytest.raises(TimelineCompilerError, match="does not exist"):
        compile_pass_a(*paths, output)


def test_malformed_mapping_is_rejected(tmp_path):
    paths, output = make_compiler_inputs(tmp_path)
    mapping = load(paths[1]); mapping["mappings"][1]["target"]["start_us"] += 1
    paths[1].write_text(json.dumps(mapping), encoding="utf-8")
    with pytest.raises(TimelineCompilerError):
        compile_pass_a(*paths, output)
