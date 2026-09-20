import pytest

from core.timeline import source_to_cut_us, validate_source_cut_map
from modules.m7_sounddesign.classification import classify
from modules.m7_sounddesign.config import SoundDesignConfig
from modules.m7_sounddesign.errors import SoundDesignError
from modules.m7_sounddesign.model import Event
from modules.m7_sounddesign.prioritization import resolve


def event(index, kind, time_us, score):
    return Event(f"candidate{index:06d}", kind, time_us, time_us, score, "context", ("origin",))


@pytest.mark.parametrize("kind,expected", [
    ("HOOK", "SOFT_IMPACT"), ("STRONG_PHRASE", "ACCENT"),
    ("SECTION_CHANGE", "SOFT_IMPACT"), ("ZOOM", "SWOOSH"),
    ("TRANSITION", "WHOOSH"),
])
def test_event_classification(kind, expected):
    assert classify(event(0, kind, 0, .8)).sound_type == expected


@pytest.mark.parametrize("context,expected", [
    ("icon_graphic concept", "POP"), ("icon_graphic cta concept", "CLICK"),
    ("broll movement", "WHOOSH"),
])
def test_visual_classification_uses_context(context, expected):
    value = Event("candidate000000", "VISUAL_APPEARANCE", 0, 0, .9, context, ("origin",))
    assert classify(value).sound_type == expected


def test_conflict_priority_prefers_visual_at_equal_score():
    events = [event(0, "ZOOM", 1_000_000, .8), event(1, "VISUAL_APPEARANCE", 1_100_000, .8)]
    _, kept, losers, _ = resolve(events, SoundDesignConfig(minimum_gap_us=1))
    assert kept == {"candidate000001"}
    assert losers == {"candidate000000": "candidate000001"}


def test_rolling_density_limit_keeps_only_highest_scores():
    events = [event(0, "HOOK", 0, .9), event(1, "SECTION_CHANGE", 10_000_000, .7),
              event(2, "ZOOM", 20_000_000, .65)]
    config = SoundDesignConfig(minimum_gap_us=1, conflict_window_us=1,
                               maximum_sfx_per_window=2)
    _, kept, _, density_losers = resolve(events, config)
    assert kept == {"candidate000000", "candidate000001"}
    assert density_losers == {"candidate000002"}


def test_shared_source_cut_conversion_uses_integer_offsets():
    mappings = [{"source": {"start_us": 2_000_000, "end_us": 3_000_000},
                 "target": {"start_us": 0, "end_us": 1_000_000}}]
    validate_source_cut_map(mappings, 1_000_000)
    assert source_to_cut_us(2_250_000, mappings) == 250_000
    assert source_to_cut_us(1_999_999, mappings) is None


def test_invalid_map_is_rejected():
    mappings = [{"source": {"start_us": 0, "end_us": 10},
                 "target": {"start_us": 1, "end_us": 11}}]
    with pytest.raises(SoundDesignError, match="contiguous"):
        validate_source_cut_map(mappings, 11, SoundDesignError)


@pytest.mark.parametrize("kwargs", [
    {"minimum_gap_us": 0}, {"conflict_window_us": 0}, {"maximum_sfx_per_window": 0},
    {"proposal_threshold": 2}, {"review_threshold": .9, "proposal_threshold": .8},
])
def test_invalid_config_is_rejected(kwargs):
    with pytest.raises(ValueError):
        SoundDesignConfig(**kwargs)
