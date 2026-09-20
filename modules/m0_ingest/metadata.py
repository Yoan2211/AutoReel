"""Convert FFprobe metadata to the versioned M0 contract."""

from fractions import Fraction

from core.time import seconds_to_us, ticks_to_us
from .probe import IngestError


def _time(stream: dict, key: str, default: int | None = None) -> int | None:
    ticks_key = {"duration": "duration_ts", "start_time": "start_pts"}[key]
    if stream.get(ticks_key) not in (None, "N/A") and stream.get("time_base"):
        return ticks_to_us(int(stream[ticks_key]), stream["time_base"])
    if stream.get(key) not in (None, "N/A"):
        return seconds_to_us(stream[key])
    return default


def _rate(value: str | None) -> str | None:
    if value in (None, "0/0", "N/A"):
        return None
    result = Fraction(value)
    return str(result) if result > 0 else None


def normalize(data: dict) -> tuple[dict, list[str]]:
    try:
        streams = data["streams"]
        videos = [s for s in streams if s.get("codec_type") == "video"
                  and not s.get("disposition", {}).get("attached_pic", 0)]
        videos.sort(key=lambda s: (not s.get("disposition", {}).get("default", 0), s["index"]))
        if not videos:
            raise IngestError("No video stream")
        video = videos[0]
        fmt = data.get("format", {})
        if not {"mov", "mp4"}.intersection(fmt.get("format_name", "").split(",")):
            raise IngestError("Only MP4/MOV containers are supported by M0 v1")
        duration = _time(video, "duration")
        duration_origin = "video_stream"
        start = _time(video, "start_time", 0)
        if duration is None:
            # Container duration can describe a longer audio track. Mark the estimate.
            duration = _time(fmt, "duration")
            duration_origin = "container_estimate"
        if duration is None or duration <= 0:
            raise IngestError("Missing or non-positive duration")
        width, height = int(video["width"]), int(video["height"])
        if width <= 0 or height <= 0:
            raise IngestError("Invalid video dimensions")
        rotation = float(video.get("tags", {}).get("rotate", 0))
        for side in video.get("side_data_list", []):
            if "rotation" in side:
                rotation = float(side["rotation"])
        if rotation % 90 != 0:
            raise IngestError("Non-orthogonal rotation requires explicit support")
        rotation = int(rotation) % 360
        transfer = video.get("color_transfer")
        hdr = {"arib-std-b67": "HLG", "smpte2084": "PQ"}.get(transfer, "UNKNOWN")
        if transfer in ("bt709", "smpte170m", "iec61966-2-1"):
            hdr = "SDR"
        warnings = []
        if hdr in ("HLG", "PQ"):
            warnings.append("HDR_SOURCE_REQUIRES_COLOR_MANAGEMENT")
        if hdr == "UNKNOWN":
            warnings.append("COLOR_TRANSFER_UNKNOWN")
        if duration_origin == "container_estimate":
            warnings.append("VIDEO_DURATION_ESTIMATED_FROM_CONTAINER")
        if len(videos) > 1:
            warnings.append("MULTIPLE_VIDEO_STREAMS_PRIMARY_SELECTED")
        audio = []
        for stream in streams:
            if stream.get("codec_type") == "audio":
                audio.append({"stream_index": int(stream["index"]),
                              "codec": stream.get("codec_name", "unknown"),
                              "sample_rate_hz": int(stream["sample_rate"]),
                              "channels": int(stream["channels"]),
                              "start_us": _time(stream, "start_time", 0),
                              "duration_us": _time(stream, "duration")})
        if not audio:
            warnings.append("NO_AUDIO_STREAM")
        return {
            "time_domain": "SOURCE", "start_us": start, "duration_us": duration,
            "duration_origin": duration_origin,
            "video": {"stream_index": int(video["index"]),
                      "codec": video.get("codec_name", "unknown"),
                      "width": width, "height": height,
                      "display_width": height if rotation % 180 else width,
                      "display_height": width if rotation % 180 else height,
                      "rotation_degrees": rotation,
                      "sample_aspect_ratio": video.get("sample_aspect_ratio", "1:1"),
                      "avg_frame_rate": _rate(video.get("avg_frame_rate")),
                      "nominal_frame_rate": _rate(video.get("r_frame_rate")),
                      "frame_timing": "UNDETERMINED",
                      "pixel_format": video.get("pix_fmt"),
                      "color_primaries": video.get("color_primaries"),
                      "color_transfer": transfer, "color_space": video.get("color_space"),
                      "color_range": video.get("color_range"), "dynamic_range": hdr},
            "audio": audio,
        }, warnings
    except (KeyError, TypeError, ValueError, ZeroDivisionError, OverflowError) as exc:
        if isinstance(exc, IngestError):
            raise
        raise IngestError(f"Invalid media metadata: {exc}") from exc
