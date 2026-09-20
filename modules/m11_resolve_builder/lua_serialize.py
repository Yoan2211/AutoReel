from __future__ import annotations

import math
from typing import Any


def _quote(value: str) -> str:
    return (
        '"'
        + value.replace("\\", "\\\\")
        .replace('"', '\\"')
        .replace("\r", "\\r")
        .replace("\n", "\\n")
        .replace("\t", "\\t")
        + '"'
    )


def to_lua(value: Any, indent: int = 0) -> str:
    if value is None:
        return "nil"
    if value is True:
        return "true"
    if value is False:
        return "false"
    if isinstance(value, str):
        return _quote(value)
    if type(value) is int:
        return str(value)
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError("Lua serializer refuses non-finite floats")
        return repr(value)
    if isinstance(value, list):
        if not value:
            return "{}"
        inner = ",\n".join(
            " " * (indent + 2) + to_lua(item, indent + 2) for item in value
        )
        return "{\n" + inner + "\n" + " " * indent + "}"
    if isinstance(value, dict):
        if not value:
            return "{}"
        rows = []
        for key in sorted(value):
            rows.append(
                " " * (indent + 2)
                + "["
                + _quote(str(key))
                + "] = "
                + to_lua(value[key], indent + 2)
            )
        return "{\n" + ",\n".join(rows) + "\n" + " " * indent + "}"
    raise TypeError(f"Cannot serialize {type(value).__name__} to Lua")
