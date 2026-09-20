from __future__ import annotations

from fractions import Fraction


def parse_fps(value: str | int | Fraction) -> Fraction:
    if isinstance(value, Fraction):
        fps = value
    elif type(value) is int:
        fps = Fraction(value, 1)
    elif isinstance(value, str):
        text = value.strip()
        if not text:
            raise ValueError("FPS cannot be empty")
        fps = Fraction(text)
    else:
        raise ValueError("FPS must be an integer, rational string, or Fraction")
    if fps <= 0:
        raise ValueError("FPS must be positive")
    return fps


def us_to_frame(timestamp_us: int, fps: str | int | Fraction) -> int:
    """Map a microsecond timestamp to the nearest frame using exact arithmetic."""
    if type(timestamp_us) is not int:
        raise ValueError("timestamp_us must be an integer")
    rate = parse_fps(fps)
    value = Fraction(timestamp_us, 1_000_000) * rate
    sign = -1 if value < 0 else 1
    num = abs(value.numerator)
    den = value.denominator
    return sign * ((2 * num + den) // (2 * den))


def interval_us_to_frames(
    start_us: int,
    end_us: int,
    fps: str | int | Fraction,
) -> tuple[int, int]:
    if type(start_us) is not int or type(end_us) is not int:
        raise ValueError("Interval timestamps must be integers")
    if start_us >= end_us:
        raise ValueError("Interval must have positive duration")
    start = us_to_frame(start_us, fps)
    end = us_to_frame(end_us, fps)
    if end <= start:
        end = start + 1
    return start, end
