import hashlib
from pathlib import Path

from .errors import TimelineCompilerError


TRACKS = (("V1", "VIDEO", 1, "SOURCE_VIDEO"), ("V2", "VIDEO", 2, "VISUALS_BROLL"),
          ("V3", "VIDEO", 3, "RESERVED_GRAPHICS_CAPTIONS"),
          ("A1", "AUDIO", 1, "SOURCE_VOICE"), ("A2", "AUDIO", 2, "MUSIC"),
          ("A3", "AUDIO", 3, "SFX"))


def verify_source(source):
    path = Path(source["path"])
    if not path.is_file() or path.stat().st_size != source["size_bytes"]:
        raise TimelineCompilerError("Original SOURCE asset does not exist or changed size")
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    if digest.hexdigest() != source["sha256"]:
        raise TimelineCompilerError("Original SOURCE asset hash changed")


def _range(event):
    return event["timeline_start_us"], event["timeline_end_us"]


def validate_tracks(tracks, duration_us):
    if [(t["id"], t["kind"], t["index"], t["role"]) for t in tracks] != list(TRACKS):
        raise TimelineCompilerError("Invalid track layout")
    if tracks[2]["events"]:
        raise TimelineCompilerError("V3 must remain reserved in Pass A")
    for track in tracks:
        ordered = sorted(track["events"], key=_range)
        if ordered != track["events"]:
            raise TimelineCompilerError(f"Track {track['id']} events are unordered")
        for event in ordered:
            start, end = _range(event)
            if type(start) is not int or type(end) is not int or start < 0 or start >= end or end > duration_us:
                raise TimelineCompilerError(f"Track {track['id']} has incoherent timestamps or duration <= 0")
        for left, right in zip(ordered, ordered[1:]):
            if left["timeline_end_us"] > right["timeline_start_us"]:
                raise TimelineCompilerError(f"Forbidden overlap on track {track['id']}")
    for track_id in ("V1", "A1"):
        track = next(item for item in tracks if item["id"] == track_id)
        if track_id == "A1" and not track["events"]:
            continue
        cursor = 0
        for event in track["events"]:
            if event["timeline_start_us"] != cursor:
                raise TimelineCompilerError(f"Track {track_id} does not cover the program contiguously")
            cursor = event["timeline_end_us"]
        if cursor != duration_us:
            raise TimelineCompilerError(f"Track {track_id} duration disagrees with M3")
