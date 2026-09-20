"""FFprobe process boundary: read metadata without transcoding."""

import json
import subprocess
from pathlib import Path


class IngestError(ValueError):
    """An input cannot safely produce an ingest manifest."""


def probe_media(source: Path, executable: str, timeout_s: int) -> dict:
    command = [executable, "-v", "error", "-show_format", "-show_streams",
               "-of", "json", str(source)]
    try:
        result = subprocess.run(command, capture_output=True, text=True,
                                encoding="utf-8", errors="replace",
                                timeout=timeout_s, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise IngestError(f"FFprobe unavailable or timed out: {exc}") from exc
    if result.returncode:
        raise IngestError(f"FFprobe failed: {result.stderr.strip()[:1000]}")
    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise IngestError("Invalid FFprobe JSON") from exc
    if not isinstance(data, dict) or not isinstance(data.get("streams"), list):
        raise IngestError("FFprobe response has no stream list")
    return data
