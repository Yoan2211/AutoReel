import base64
import subprocess
import wave

import pytest

from modules.m6_asset_manager.config import AssetManagerConfig
from modules.m6_asset_manager.library import scan
from modules.m6_asset_manager.probe import FFprobeMediaProbe

from .fixtures import add_asset


def test_real_ffprobe_extracts_audio_metadata(tmp_path):
    path = tmp_path / "sfx" / "whoosh.wav"
    path.parent.mkdir()
    with wave.open(str(path), "wb") as output:
        output.setnchannels(1)
        output.setsampwidth(2)
        output.setframerate(48_000)
        output.writeframes(b"\x00\x00" * 4_800)
    metadata = FFprobeMediaProbe().probe(path, "SFX")
    assert metadata["media_kind"] == "AUDIO"
    assert metadata["sample_rate_hz"] == 48_000
    assert metadata["channels"] == 1
    assert 99_000 <= metadata["duration_us"] <= 101_000


def test_real_ffprobe_extracts_image_dimensions(tmp_path):
    path = tmp_path / "graphics" / "pixel.png"
    path.parent.mkdir()
    path.write_bytes(base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAusB9Wl2nF0AAAAASUVORK5CYII="))
    metadata = FFprobeMediaProbe().probe(path, "GRAPHIC")
    assert metadata["media_kind"] == "IMAGE"
    assert (metadata["width"], metadata["height"]) == (1, 1)


def test_real_ffprobe_extracts_broll_metadata(tmp_path):
    path = tmp_path / "broll" / "clip.mp4"
    path.parent.mkdir()
    result = subprocess.run(["ffmpeg", "-v", "error", "-f", "lavfi", "-i",
                             "color=c=black:s=64x96:d=0.2", "-an", "-y", str(path)],
                            capture_output=True, text=True, check=False,
                            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    assert result.returncode == 0, result.stderr
    metadata = FFprobeMediaProbe().probe(path, "BROLL")
    assert metadata["media_kind"] == "VIDEO"
    assert (metadata["width"], metadata["height"]) == (64, 96)
    assert metadata["duration_us"] >= 190_000


def test_library_classifies_supported_asset_families(tmp_path):
    add_asset(tmp_path, "photos/portrait.jpg")
    add_asset(tmp_path, "illustrations/diagram.png")
    add_asset(tmp_path, "graphics/icon.webp")
    add_asset(tmp_path, "broll/movement.mp4")
    add_asset(tmp_path, "sfx/click.wav")
    add_asset(tmp_path, "music/bed.mp3")
    candidates, issues = scan(tmp_path)
    assert issues == []
    assert {item.asset_type for item in candidates} == {"IMAGE", "ILLUSTRATION", "GRAPHIC", "BROLL", "SFX", "MUSIC"}


@pytest.mark.parametrize("kwargs", [
    {"resolved_score_threshold": 2}, {"review_score_threshold": .8, "resolved_score_threshold": .7},
    {"recursive": 1}, {"ffprobe_path": ""},
])
def test_invalid_config_is_rejected(kwargs):
    with pytest.raises(ValueError):
        AssetManagerConfig(**kwargs)
