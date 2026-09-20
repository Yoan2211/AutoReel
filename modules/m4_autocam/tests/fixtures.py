import hashlib
import json

from modules.m4_autocam.model import Frame


HASH = "a" * 64


def write_inputs(tmp_path, intervals=((0, 2_000_000),), *, geometry=(1920, 1080, 1920, 1080, 0)):
    tmp_path.mkdir(parents=True, exist_ok=True)
    media = tmp_path / "source.mp4"
    media.write_bytes(b"original-source-media")
    digest = hashlib.sha256(media.read_bytes()).hexdigest()
    width, height, display_width, display_height, rotation = geometry
    manifest = {
        "schema_version": "1.0.0", "module": {"id": "M0", "version": "1.0.0"},
        "source": {
            "path": str(media.resolve()), "size_bytes": media.stat().st_size, "sha256": digest,
            "time_domain": "SOURCE", "start_us": 0, "duration_us": 10_000_000,
            "duration_origin": "video_stream",
            "video": {"stream_index": 0, "codec": "h264", "width": width, "height": height,
                      "display_width": display_width, "display_height": display_height,
                      "rotation_degrees": rotation, "sample_aspect_ratio": "1:1",
                      "avg_frame_rate": "30/1", "nominal_frame_rate": "30/1",
                      "frame_timing": "UNDETERMINED", "pixel_format": "yuv420p",
                      "color_primaries": None, "color_transfer": None, "color_space": None,
                      "color_range": None, "dynamic_range": "SDR"},
            "audio": []}, "warnings": ["NO_AUDIO_STREAM"]}
    mappings = []
    cut_us = 0
    for index, (start_us, end_us) in enumerate(intervals):
        duration = end_us - start_us
        mappings.append({"id": f"map{index:06d}",
                         "source": {"time_domain": "SOURCE", "start_us": start_us, "end_us": end_us},
                         "target": {"time_domain": "CUT", "start_us": cut_us, "end_us": cut_us + duration}})
        cut_us += duration
    time_map = {
        "schema_version": "1.0.0", "module": {"id": "M3", "version": "1.0.0"},
        "stage": "smartedit", "source_time_domain": "SOURCE", "target_time_domain": "CUT",
        "source": {"transcript_path": "transcript.json", "transcript_sha256": HASH,
                   "cuts_path": "cuts.json", "cuts_sha256": HASH,
                   "speechcut_time_map_path": "speechcut.json", "speechcut_time_map_sha256": HASH,
                   "media_path": str(media.resolve()), "media_sha256": digest, "edit_plan_sha256": HASH},
        "source_start_us": 0, "source_end_us": 10_000_000,
        "output_duration_us": cut_us, "mappings": mappings}
    manifest_path, map_path = tmp_path / "source-manifest.json", tmp_path / "time-map-smartedit.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    map_path.write_text(json.dumps(time_map), encoding="utf-8")
    return manifest_path, map_path, tmp_path / "camera-plan.json", media


class FakeFrameProvider:
    def __init__(self, width=1920, height=1080):
        self.width, self.height, self.calls = width, height, []

    def frames(self, source, intervals, source_origin_us, rotation_degrees, sample_interval_us):
        self.calls.append((source, tuple(intervals), source_origin_us, rotation_degrees, sample_interval_us))
        for start_us, end_us in intervals:
            for source_us in range(start_us, end_us, sample_interval_us):
                yield Frame(source_us, None, self.width, self.height)


class FakeDetector:
    name, version, device, warnings = "fake-subject-detector", "1.0", "cpu", []

    def __init__(self, sequence):
        self.sequence = sequence
        self.index = 0

    def detect(self, frame):
        result = self.sequence[min(self.index, len(self.sequence) - 1)] if self.sequence else []
        self.index += 1
        return result
