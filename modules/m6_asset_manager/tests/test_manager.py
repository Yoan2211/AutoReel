import json

import pytest

from modules.m6_asset_manager.errors import AssetManagerError
from modules.m6_asset_manager.manager import resolve_assets

from .fixtures import FakeProbe, add_asset, make_inputs


def seed_matching_library(library):
    add_asset(library, "graphics/icon_graphic_ventes_pourcent.png")
    add_asset(library, "sfx/pop_visual.wav")
    add_asset(library, "music/clean_modern_business_low.wav")


def test_empty_library_keeps_requests_unresolved_without_inventing_paths(tmp_path):
    paths = make_inputs(tmp_path)
    manifest = resolve_assets(*paths, media_probe=FakeProbe())
    assert manifest["requests"]
    assert all(item["status"] == "UNRESOLVED" and item["asset_id"] is None for item in manifest["requests"])
    assert manifest["assets"] == []
    assert manifest["warnings"] == ["EMPTY_LIBRARY", "UNRESOLVED_REQUESTS"]


def test_local_visual_sfx_and_music_assets_are_resolved_and_validated(tmp_path):
    paths = make_inputs(tmp_path)
    seed_matching_library(paths[3])
    probe = FakeProbe()
    manifest = resolve_assets(*paths, media_probe=probe)
    types = {item["asset_type"] for item in manifest["assets"]}
    assert {"GRAPHIC", "SFX", "MUSIC"} <= types
    assert manifest["summary"]["resolved_count"] >= 3
    assert all(len(item["sha256"]) == 64 and item["size_bytes"] > 0 for item in manifest["assets"])
    assert set(probe.calls) >= {"icon_graphic_ventes_pourcent.png", "pop_visual.wav", "clean_modern_business_low.wav"}


def test_same_physical_asset_is_reused_with_one_stable_id(tmp_path):
    paths = make_inputs(tmp_path)
    seed_matching_library(paths[3])
    manifest = resolve_assets(*paths, media_probe=FakeProbe())
    graphic = next(item for item in manifest["assets"] if item["asset_type"] == "GRAPHIC")
    matching = [item for item in manifest["requests"] if item["asset_id"] == graphic["asset_id"]]
    assert len(matching) >= 2
    assert sorted(graphic["request_ids"]) == sorted(item["request_id"] for item in matching)


def test_asset_ids_are_content_stable_across_manifests(tmp_path):
    paths = make_inputs(tmp_path)
    seed_matching_library(paths[3])
    left = resolve_assets(*paths[:-1], tmp_path / "left.json", media_probe=FakeProbe())
    right = resolve_assets(*paths[:-1], tmp_path / "right.json", media_probe=FakeProbe())
    assert {item["asset_id"] for item in left["assets"]} == {item["asset_id"] for item in right["assets"]}


def test_paths_are_project_relative_when_library_is_inside_project(tmp_path):
    paths = make_inputs(tmp_path)
    seed_matching_library(paths[3])
    manifest = resolve_assets(*paths, project_root_path=tmp_path, media_probe=FakeProbe())
    assert all(item["path_kind"] == "PROJECT_RELATIVE" for item in manifest["assets"])
    assert all(item["path"].startswith("assets/") for item in manifest["assets"])


def test_invalid_best_candidate_is_skipped_for_next_valid_match(tmp_path):
    paths = make_inputs(tmp_path)
    add_asset(paths[3], "graphics/icon_graphic_ventes_pourcent.png", b"bad")
    add_asset(paths[3], "graphics/icon_graphic_ventes.png", b"good")
    manifest = resolve_assets(*paths, media_probe=FakeProbe({"icon_graphic_ventes_pourcent.png"}))
    assert "INVALID_LIBRARY_ASSETS" in manifest["warnings"]
    assert manifest["library_issues"]
    assert any(item["asset_id"] is not None for item in manifest["requests"] if item["asset_type"] == "GRAPHIC")


def test_malformed_sidecar_is_reported_and_not_used(tmp_path):
    paths = make_inputs(tmp_path)
    asset = add_asset(paths[3], "graphics/icon_graphic.png")
    asset.with_suffix(".png.asset.json").write_text("[]", encoding="utf-8")
    manifest = resolve_assets(*paths, media_probe=FakeProbe())
    assert manifest["summary"]["library_issue_count"] == 1
    assert "INVALID_LIBRARY_ASSETS" in manifest["warnings"]


def test_sidecar_tags_improve_deterministic_match(tmp_path):
    paths = make_inputs(tmp_path)
    add_asset(paths[3], "graphics/a.png", sidecar={"tags": ["icon", "graphic", "ventes", "pourcent"]})
    add_asset(paths[3], "graphics/b.png", sidecar={"tags": ["icon", "graphic"]})
    manifest = resolve_assets(*paths, media_probe=FakeProbe())
    graphic = next(item for item in manifest["assets"] if item["asset_type"] == "GRAPHIC")
    assert graphic["path"].endswith("a.png")


def test_upstream_review_can_attach_candidate_but_stays_review(tmp_path):
    sentences = ["Imagine le mécanisme de ce processus complexe.",
                 "Une explication reste calme et neutre.", "La conclusion reste sobre."]
    paths = make_inputs(tmp_path, sentences)
    add_asset(paths[3], "illustrations/illustration_mecanisme_processus.png")
    manifest = resolve_assets(*paths, media_probe=FakeProbe())
    request = next(item for item in manifest["requests"] if item["asset_type"] == "ILLUSTRATION")
    assert request["upstream_status"] == "REVIEW"
    assert request["status"] == "REVIEW" and request["asset_id"] is not None


def test_no_upstream_requests_produces_empty_manifest(tmp_path):
    paths = make_inputs(tmp_path, [])
    manifest = resolve_assets(*paths, media_probe=FakeProbe())
    assert manifest["requests"] == [] and manifest["assets"] == []
    assert manifest["summary"]["request_count"] == 0


def test_broken_music_provenance_is_rejected(tmp_path):
    paths = make_inputs(tmp_path)
    music = json.loads(paths[2].read_text(encoding="utf-8"))
    music["source"]["sound_plan_sha256"] = "f" * 64
    paths[2].write_text(json.dumps(music), encoding="utf-8")
    with pytest.raises(AssetManagerError, match="music_plan"):
        resolve_assets(*paths, media_probe=FakeProbe())


def test_existing_manifest_is_preserved(tmp_path):
    paths = make_inputs(tmp_path)
    paths[-1].write_text("user data", encoding="utf-8")
    with pytest.raises(FileExistsError):
        resolve_assets(*paths, media_probe=FakeProbe())
    assert paths[-1].read_text(encoding="utf-8") == "user data"
