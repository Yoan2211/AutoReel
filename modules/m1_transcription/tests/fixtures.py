"""Independent fixtures of the public M0 JSON contract, no M0 imports."""

import hashlib
import json
from pathlib import Path

from modules.m1_transcription.backend import Recognition, Segment, Word


def source_manifest(source: Path, *, origin_us: int = 500000, duration_us: int = 3000000) -> dict:
    return {
        "schema_version": "1.0.0", "module": {"id": "M0", "version": "1.0.0"},
        "source": {
            "path": str(source.resolve()), "size_bytes": source.stat().st_size,
            "sha256": hashlib.sha256(source.read_bytes()).hexdigest(), "time_domain": "SOURCE",
            "start_us": 0, "duration_us": duration_us, "duration_origin": "video_stream",
            "video": {"stream_index": 0, "codec": "h264", "width": 160, "height": 90,
                      "display_width": 160, "display_height": 90, "rotation_degrees": 0,
                      "sample_aspect_ratio": "1:1", "avg_frame_rate": "25",
                      "nominal_frame_rate": "25", "frame_timing": "UNDETERMINED",
                      "pixel_format": "yuv420p", "color_primaries": "bt709",
                      "color_transfer": "bt709", "color_space": "bt709", "color_range": "tv",
                      "dynamic_range": "SDR"},
            "audio": [{"stream_index": 1, "codec": "pcm_s16le", "sample_rate_hz": 16000,
                       "channels": 1, "start_us": origin_us, "duration_us": duration_us}]},
        "warnings": [],
    }


def save_manifest(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")


def recognition() -> Recognition:
    return Recognition("fr", 0.98, (
        Segment("0.1", "1.2", " Euh, je je teste.", 0.01, (
            Word("0.1", "0.3", " Euh,", 0.91), Word("0.4", "0.5", " je", 0.95),
            Word("0.6", "0.7", " je", 0.96), Word("0.9", "1.2", " teste.", 0.99))),
    ), "test-engine", "1.0", "cpu", "int8")
