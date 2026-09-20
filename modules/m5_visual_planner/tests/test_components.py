import pytest

from modules.m5_visual_planner.config import VisualPlannerConfig
from modules.m5_visual_planner.time_mapping import best_retained_window, validate_mappings
from modules.m5_visual_planner.errors import VisualPlannerError


def test_best_retained_window_prefers_longest_then_earliest():
    mappings = [
        {"source": {"start_us": 0, "end_us": 400}, "target": {"start_us": 0, "end_us": 400}},
        {"source": {"start_us": 600, "end_us": 1000}, "target": {"start_us": 400, "end_us": 800}},
    ]
    assert best_retained_window(0, 1000, mappings) == (0, 400, 0, 400)


def test_invalid_mapping_is_rejected():
    mappings = [{"source": {"start_us": 0, "end_us": 10},
                 "target": {"start_us": 1, "end_us": 11}}]
    with pytest.raises(VisualPlannerError, match="contiguous"):
        validate_mappings(mappings, 11)


@pytest.mark.parametrize("kwargs", [
    {"minimum_gap_us": 0}, {"maximum_visuals_per_section": 0},
    {"minimum_duration_us": 2_000_000, "target_duration_us": 1_000_000},
    {"auto_confidence_threshold": 2}, {"auto_confidence_threshold": True},
])
def test_invalid_configuration_is_rejected(kwargs):
    with pytest.raises(ValueError):
        VisualPlannerConfig(**kwargs)
