import json
import subprocess

from core.time import seconds_to_us

from .errors import AssetManagerError


class FFprobeMediaProbe:
    def __init__(self, executable="ffprobe"):
        self.executable = executable

    def probe(self, path, asset_type):
        command = [self.executable, "-v", "error", "-show_streams", "-show_format", "-of", "json", str(path)]
        try:
            result = subprocess.run(command, capture_output=True, text=True, encoding="utf-8",
                                    errors="replace", check=False, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        except OSError as exc:
            raise AssetManagerError(f"Cannot execute FFprobe: {self.executable}") from exc
        if result.returncode != 0:
            raise AssetManagerError(f"FFprobe rejected asset: {result.stderr.strip() or path}")
        try:
            value = json.loads(result.stdout)
        except json.JSONDecodeError as exc:
            raise AssetManagerError("FFprobe returned invalid JSON") from exc
        streams = value.get("streams", [])
        video = next((item for item in streams if item.get("codec_type") == "video"), None)
        audio = next((item for item in streams if item.get("codec_type") == "audio"), None)
        if asset_type in {"IMAGE", "ILLUSTRATION", "GRAPHIC", "BROLL"} and video is None:
            raise AssetManagerError("Expected a decodable visual stream")
        if asset_type in {"SFX", "MUSIC"} and audio is None:
            raise AssetManagerError("Expected a decodable audio stream")
        stream = audio if asset_type in {"SFX", "MUSIC"} else video
        duration_text = stream.get("duration") or value.get("format", {}).get("duration")
        duration_us = None
        if duration_text not in (None, "N/A"):
            duration_us = max(0, seconds_to_us(duration_text))
        return {"media_kind": "AUDIO" if audio is stream else "VIDEO" if asset_type == "BROLL" else "IMAGE",
                "format": path.suffix.casefold().lstrip("."), "codec": stream.get("codec_name"),
                "duration_us": duration_us,
                "width": int(stream["width"]) if stream.get("width") is not None else None,
                "height": int(stream["height"]) if stream.get("height") is not None else None,
                "sample_rate_hz": int(stream["sample_rate"]) if stream.get("sample_rate") is not None else None,
                "channels": int(stream["channels"]) if stream.get("channels") is not None else None,
                "loudness_lufs": None}
