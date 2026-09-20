import hashlib

import pytest

from modules.m10_timeline_compiler.assets import AssetIndex
from modules.m10_timeline_compiler.audio import source_audio_events
from modules.m10_timeline_compiler.errors import TimelineCompilerError
from modules.m10_timeline_compiler.projection import (project_source_point, project_source_range,
                                                       require_exact_projection, timeline_range)
from modules.m10_timeline_compiler.validation import validate_tracks


MAPPINGS = [
    {"source": {"start_us": 1_000_000, "end_us": 2_000_000},
     "target": {"start_us": 0, "end_us": 1_000_000}},
    {"source": {"start_us": 4_000_000, "end_us": 6_000_000},
     "target": {"start_us": 1_000_000, "end_us": 3_000_000}},
]


def test_projection_keeps_source_and_cut_distinct():
    assert project_source_range(4_200_000, 4_700_000, MAPPINGS) == [
        (4_200_000, 4_700_000, 1_200_000, 1_700_000)]
    assert project_source_point(4_500_000, MAPPINGS) == 1_500_000


def test_deleted_source_point_is_not_projected():
    assert project_source_point(3_000_000, MAPPINGS) is None


def test_exact_projection_rejects_crossing_deleted_material():
    with pytest.raises(TimelineCompilerError, match="removed interval"):
        require_exact_projection(1_500_000, 4_500_000, 500_000, 1_500_000, MAPPINGS, "visual")


@pytest.mark.parametrize("start,end", [(0, 0), (2, 1), (-1, 1)])
def test_invalid_or_non_positive_ranges_are_rejected(start, end):
    with pytest.raises(TimelineCompilerError):
        timeline_range(start, end)


def test_invalid_track_layout_is_rejected():
    with pytest.raises(TimelineCompilerError, match="Invalid track"):
        validate_tracks([], 1_000_000)


def test_forbidden_overlap_is_rejected():
    specs = (("V1", "VIDEO", 1, "SOURCE_VIDEO"), ("V2", "VIDEO", 2, "VISUALS_BROLL"),
             ("V3", "VIDEO", 3, "RESERVED_GRAPHICS_CAPTIONS"), ("A1", "AUDIO", 1, "SOURCE_VOICE"),
             ("A2", "AUDIO", 2, "MUSIC"), ("A3", "AUDIO", 3, "SFX"))
    tracks = [{"id": a, "kind": b, "index": c, "role": d, "events": []} for a, b, c, d in specs]
    tracks[1]["events"] = [{"timeline_start_us": 0, "timeline_end_us": 800_000},
                            {"timeline_start_us": 700_000, "timeline_end_us": 900_000}]
    with pytest.raises(TimelineCompilerError, match="Forbidden overlap"):
        validate_tracks(tracks, 1_000_000)


def test_resolved_missing_asset_is_rejected(tmp_path):
    content = b"asset"; digest = hashlib.sha256(content).hexdigest()
    manifest = {"library": {"project_root": str(tmp_path)},
                "requests": [{"request_id": "M5:x", "origin_module": "M5", "status": "RESOLVED", "asset_id": "gfx_x"}],
                "assets": [{"asset_id": "gfx_x", "path": "missing.png", "path_kind": "PROJECT_RELATIVE",
                            "size_bytes": len(content), "sha256": digest}]}
    index = AssetIndex(manifest)
    with pytest.raises(TimelineCompilerError, match="does not exist"):
        index.resolved(manifest["requests"][0])


def test_multiple_source_audio_streams_are_rejected_as_ambiguous():
    media = {"audio": [{"stream_index": 1}, {"stream_index": 2}]}
    with pytest.raises(TimelineCompilerError, match="ambiguous"):
        source_audio_events(media, MAPPINGS)
