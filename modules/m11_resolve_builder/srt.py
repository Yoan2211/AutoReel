from __future__ import annotations

from pathlib import Path


def _timestamp(us: int) -> str:
    if type(us) is not int or us < 0:
        raise ValueError("SRT timestamp must be a non-negative integer")
    ms = us // 1000
    hours, rem = divmod(ms, 3_600_000)
    minutes, rem = divmod(rem, 60_000)
    seconds, millis = divmod(rem, 1000)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d},{millis:03d}"


def render_srt(events: list[dict]) -> str:
    blocks = []
    for index, event in enumerate(events, start=1):
        lines = event.get("lines") or [event["text"]]
        text = "\n".join(str(line) for line in lines)
        blocks.append(
            f"{index}\n"
            f"{_timestamp(event['timeline_start_us'])} --> "
            f"{_timestamp(event['timeline_end_us'])}\n"
            f"{text}\n"
        )
    return "\n".join(blocks)


def write_srt(path: Path, events: list[dict]) -> None:
    if path.exists() or path.is_symlink():
        raise FileExistsError(f"Refusing to overwrite: {path}")
    path.write_text(render_srt(events), encoding="utf-8-sig")
