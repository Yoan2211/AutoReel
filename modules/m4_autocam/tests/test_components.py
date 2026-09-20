import pytest

from modules.m4_autocam.config import AutoCamConfig
from modules.m4_autocam.framing import calculate
from modules.m4_autocam.model import Detection
from modules.m4_autocam.smoothing import CameraSmoother
from modules.m4_autocam.tracking import SubjectTracker


def test_tracker_expires_subject_after_hold_window():
    tracker = SubjectTracker(500_000)
    detection = Detection("face", .4, .2, .1, .2, .9)
    assert tracker.update(0, [detection])[0][0] == 1
    assert tracker.update(500_000, [])[0][2] is True
    assert tracker.update(500_001, []) == []


def test_widely_separated_people_are_flagged_for_review():
    subjects = [(1, Detection("person", .02, .1, .2, .8, .9), False),
                (2, Detection("person", .78, .1, .2, .8, .9), False)]
    state = calculate(1920, 1080, subjects, AutoCamConfig())
    assert state.warning == "SUBJECTS_EXCEED_VERTICAL_FRAME"
    assert state.zoom == 1


def test_smoother_reduces_camera_displacement():
    config = AutoCamConfig(smoothing_alpha=.2)
    left = calculate(1920, 1080, [(1, Detection("face", .1, .2, .1, .2, .9), False)], config)
    right = calculate(1920, 1080, [(1, Detection("face", .7, .2, .1, .2, .9), False)], config)
    smoother = CameraSmoother(.2)
    first = smoother.update(left)
    smoothed = smoother.update(right)
    assert abs(smoothed.center_x - first.center_x) < abs(right.center_x - first.center_x)


@pytest.mark.parametrize("kwargs", [
    {"sample_interval_us": 0}, {"device": "tpu"}, {"smoothing_alpha": 2},
    {"natural_zoom_max": 1.16}, {"hard_zoom_max": 1.16}, {"cpu_fallback": 1},
])
def test_invalid_configuration_is_rejected(kwargs):
    with pytest.raises(ValueError):
        AutoCamConfig(**kwargs)
