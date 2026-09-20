import json

import pytest

from modules.m4_autocam.autocam import autocam
from modules.m4_autocam.config import AutoCamConfig
from modules.m4_autocam.errors import AutoCamError
from modules.m4_autocam.model import Detection

from .fixtures import FakeDetector, FakeFrameProvider, write_inputs


def face(x=.4, y=.2, width=.12, height=.22):
    return Detection("face", x, y, width, height, .95)


def run(tmp_path, detections, *, intervals=((0, 2_000_000),), provider=None, config=None, geometry=(1920, 1080, 1920, 1080, 0)):
    manifest, time_map, output, _ = write_inputs(tmp_path, intervals, geometry=geometry)
    provider = provider or FakeFrameProvider(geometry[2], geometry[3])
    plan = autocam(manifest, time_map, output, config or AutoCamConfig(),
                   frame_provider=provider, detector=FakeDetector(detections))
    assert json.loads(output.read_text(encoding="utf-8")) == plan
    return plan, provider


def test_fixed_person_produces_stable_sparse_plan(tmp_path):
    plan, _ = run(tmp_path, [[face()]] * 8)
    shot = plan["shots"][0]
    assert plan["summary"] == {"source_interval_count": 1, "frames_analyzed": 8,
                               "detections": 8, "keyframes": 1}
    assert shot["source_start_us"] == 0 and shot["source_end_us"] == 2_000_000
    assert shot["keyframes"][0]["subject_track_ids"] == [1]
    assert shot["keyframes"][0]["zoom"] <= 1.08


def test_moving_person_is_tracked_and_smoothed(tmp_path):
    sequence = [[face(x=x)] for x in (.10, .20, .30, .40)]
    config = AutoCamConfig(sample_interval_us=250_000, smoothing_alpha=.25,
                           center_change_threshold=0, zoom_change_threshold=1)
    plan, _ = run(tmp_path, sequence, intervals=((0, 1_000_000),), config=config)
    keyframes = plan["shots"][0]["keyframes"]
    centers = [item["center_x"] for item in keyframes]
    assert all(item["subject_track_ids"] == [1] for item in keyframes)
    assert centers == sorted(centers)
    assert centers[-1] < .46  # raw final centre is .46; smoothing must lag it.


def test_two_people_are_kept_in_one_conservative_frame(tmp_path):
    pair = [face(.30), face(.55)]
    plan, _ = run(tmp_path, [pair] * 8)
    keyframe = plan["shots"][0]["keyframes"][0]
    assert keyframe["subject_track_ids"] == [1, 2]
    assert keyframe["zoom"] == 1
    assert .4 < keyframe["center_x"] < .6


def test_temporarily_lost_face_keeps_track_without_camera_jump(tmp_path):
    plan, _ = run(tmp_path, [[face()], [], [], [face(.41)]], intervals=((0, 1_000_000),),
                  config=AutoCamConfig(center_change_threshold=0, zoom_change_threshold=1))
    keyframes = plan["shots"][0]["keyframes"]
    assert keyframes[1]["predicted_track_ids"] == [1]
    assert keyframes[2]["predicted_track_ids"] == [1]
    assert keyframes[3]["subject_track_ids"] == [1]
    assert all(item["warning"] is None for item in keyframes)


def test_deleted_source_ranges_are_never_requested_or_analyzed(tmp_path):
    provider = FakeFrameProvider()
    plan, provider = run(tmp_path, [[face()]] * 8, intervals=((0, 1_000_000), (3_000_000, 4_000_000)), provider=provider)
    requested = [call[1] for call in provider.calls]
    assert requested == [((0, 1_000_000),), ((3_000_000, 4_000_000),)]
    assert plan["summary"]["frames_analyzed"] == 8
    assert [(s["source_start_us"], s["source_end_us"]) for s in plan["shots"]] == [(0, 1_000_000), (3_000_000, 4_000_000)]


@pytest.mark.parametrize("geometry,frame_size,expected_crop", [
    ((1920, 1080, 1920, 1080, 0), (1920, 1080), (608, 1080)),
    ((1080, 1920, 1080, 1920, 0), (1080, 1920), (1080, 1920)),
    ((1920, 1080, 1080, 1920, 90), (1080, 1920), (1080, 1920)),
])
def test_landscape_portrait_and_rotation_geometry(tmp_path, geometry, frame_size, expected_crop):
    provider = FakeFrameProvider(*frame_size)
    plan, provider = run(tmp_path, [[]], intervals=((0, 250_000),), provider=provider, geometry=geometry)
    keyframe = plan["shots"][0]["keyframes"][0]
    assert provider.calls[0][3] == geometry[4]
    assert (keyframe["crop_width"], keyframe["crop_height"]) == expected_crop


def test_jitter_is_smoothed_and_does_not_create_permanent_reframes(tmp_path):
    sequence = [[face(x=x)] for x in (.400, .405, .397, .404, .399, .403, .398, .400)]
    plan, _ = run(tmp_path, sequence)
    assert len(plan["shots"][0]["keyframes"]) == 1


def test_zoom_is_never_excessive(tmp_path):
    normal, _ = run(tmp_path / "normal", [[face(height=.20)]])
    tiny, _ = run(tmp_path / "tiny", [[face(height=.05)]])
    assert normal["shots"][0]["keyframes"][0]["zoom"] <= 1.08
    assert tiny["shots"][0]["keyframes"][0]["zoom"] <= 1.15


def test_source_identity_mismatch_is_rejected(tmp_path):
    manifest, time_map, output, _ = write_inputs(tmp_path)
    value = json.loads(time_map.read_text(encoding="utf-8"))
    value["source"]["media_sha256"] = "b" * 64
    time_map.write_text(json.dumps(value), encoding="utf-8")
    with pytest.raises(AutoCamError, match="identities disagree"):
        autocam(manifest, time_map, output, frame_provider=FakeFrameProvider(), detector=FakeDetector([]))


def test_changed_source_is_rejected(tmp_path):
    manifest, time_map, output, media = write_inputs(tmp_path)
    media.write_bytes(b"changed")
    with pytest.raises(AutoCamError, match="missing or changed"):
        autocam(manifest, time_map, output, frame_provider=FakeFrameProvider(), detector=FakeDetector([]))


def test_existing_output_is_preserved(tmp_path):
    manifest, time_map, output, _ = write_inputs(tmp_path)
    output.write_text("user data", encoding="utf-8")
    with pytest.raises(FileExistsError):
        autocam(manifest, time_map, output, frame_provider=FakeFrameProvider(), detector=FakeDetector([]))
    assert output.read_text(encoding="utf-8") == "user data"
