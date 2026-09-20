import pytest

from core.time_ranges import cut_range_to_source_ranges, source_range_to_cut_ranges
from modules.m8_music.config import MusicPlannerConfig


MAPPINGS = [
    {"source": {"start_us": 1_000_000, "end_us": 2_000_000},
     "target": {"start_us": 0, "end_us": 1_000_000}},
    {"source": {"start_us": 3_000_000, "end_us": 4_000_000},
     "target": {"start_us": 1_000_000, "end_us": 2_000_000}},
]


def test_source_range_mapping_never_bridges_deleted_media():
    assert source_range_to_cut_ranges(1_500_000, 3_500_000, MAPPINGS) == [
        (500_000, 1_000_000), (1_000_000, 1_500_000)]


def test_cut_range_mapping_preserves_all_source_intervals():
    assert cut_range_to_source_ranges(500_000, 1_500_000, MAPPINGS) == [
        {"source_start_us": 1_500_000, "source_end_us": 2_000_000},
        {"source_start_us": 3_000_000, "source_end_us": 3_500_000}]


@pytest.mark.parametrize("kwargs", [
    {"minimum_music_duration_us": 0}, {"proposal_duration_us": 1, "minimum_music_duration_us": 2},
    {"speech_gain_db": -24}, {"speech_gain_db": -31}, {"no_speech_gain_db": -40},
    {"speech_gain_db": True},
])
def test_invalid_configuration_is_rejected(kwargs):
    with pytest.raises(ValueError):
        MusicPlannerConfig(**kwargs)
