"""Only authority for temporal conversion. No binary floating point timestamps."""

from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from enum import Enum
from fractions import Fraction


class TimeDomain(str, Enum):
    SOURCE = "SOURCE"
    CUT = "CUT"
    TIMELINE = "TIMELINE"


def seconds_to_us(value: str | int | Decimal) -> int:
    """Round decimal seconds to nearest µs, ties away from zero."""
    if isinstance(value, (bool, float)):
        raise ValueError("Use decimal text, never a float timestamp")
    try:
        seconds = Decimal(value)
        if not seconds.is_finite():
            raise ValueError("Non-finite timestamp")
        return int((seconds * 1_000_000).to_integral_value(rounding=ROUND_HALF_UP))
    except (InvalidOperation, TypeError) as exc:
        raise ValueError("Invalid timestamp") from exc


def ticks_to_us(ticks: int, time_base: str) -> int:
    """Convert stream ticks exactly, with the same tie rule as seconds_to_us."""
    if type(ticks) is not int:
        raise ValueError("Ticks must be integers")
    try:
        base = Fraction(time_base)
        if base <= 0:
            raise ValueError("Time base must be positive")
        value = ticks * base * 1_000_000
        sign = -1 if value < 0 else 1
        numerator = abs(value.numerator)
        return sign * ((2 * numerator + value.denominator) // (2 * value.denominator))
    except (ZeroDivisionError, TypeError) as exc:
        raise ValueError("Invalid time base") from exc


def us_to_seconds_text(value_us: int) -> str:
    """Format integer microseconds as exact decimal seconds for media tools."""
    if type(value_us) is not int:
        raise ValueError("Timestamp must be integer microseconds")
    sign = "-" if value_us < 0 else ""
    whole, remainder = divmod(abs(value_us), 1_000_000)
    return f"{sign}{whole}.{remainder:06d}"


def seconds_to_timestamp_us(value: str | int | Decimal, origin_us: int) -> int:
    """Place a relative decimal ASR timestamp on a declared temporal origin."""
    if type(origin_us) is not int:
        raise ValueError("Origin must be integer microseconds")
    return origin_us + seconds_to_us(value)
