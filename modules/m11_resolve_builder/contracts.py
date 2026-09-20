from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from .errors import ContractError, MediaVerificationError


def sha256_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(chunk_size), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ContractError(f"Cannot read JSON: {path}") from exc
    if not isinstance(value, dict):
        raise ContractError(f"Expected JSON object: {path}")
    return value


def _project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def validate_timeline(value: dict[str, Any]) -> None:
    schema_path = _project_root() / "core" / "schemas" / "timeline-1.0.0.json"
    if not schema_path.is_file():
        raise ContractError(f"Missing timeline schema: {schema_path}")

    try:
        import jsonschema
    except ImportError:
        if value.get("schema_version") != "1.0.0":
            raise ContractError("timeline.json schema_version must be 1.0.0")
        if value.get("stage") != "timeline_compiler_final":
            raise ContractError("timeline.json is not M10 Final")
        tracks = value.get("tracks")
        if not isinstance(tracks, list) or {x.get("id") for x in tracks if isinstance(x, dict)} != {
            "V1", "V2", "V3", "A1", "A2", "A3"
        }:
            raise ContractError("timeline.json does not contain the six M10 tracks")
        return

    schema = load_json(schema_path)
    try:
        jsonschema.Draft202012Validator(schema).validate(value)
    except jsonschema.ValidationError as exc:
        location = ".".join(str(x) for x in exc.absolute_path)
        raise ContractError(
            "timeline.json does not validate against timeline-1.0.0.json"
            + (f" at {location}" if location else "")
            + f": {exc.message}"
        ) from exc


def resolve_path(raw: str, *, base: Path) -> Path:
    path = Path(raw).expanduser()
    if not path.is_absolute():
        path = base / path
    try:
        return path.resolve(strict=True)
    except FileNotFoundError as exc:
        raise MediaVerificationError(f"Referenced file does not exist: {path}") from exc


def verify_digest(path: Path, expected: str, label: str) -> None:
    if not isinstance(expected, str) or len(expected) != 64:
        raise ContractError(f"{label}: invalid SHA-256 contract")
    actual = sha256_file(path)
    if actual != expected:
        raise MediaVerificationError(
            f"{label}: SHA-256 mismatch for {path}\nexpected={expected}\nactual={actual}"
        )


def load_final_timeline(path: str | Path) -> tuple[Path, dict[str, Any], str]:
    timeline_path = Path(path).expanduser().resolve(strict=True)
    value = load_json(timeline_path)
    validate_timeline(value)
    return timeline_path, value, sha256_file(timeline_path)


def load_source_manifest(
    timeline_path: Path,
    timeline: dict[str, Any],
) -> tuple[Path, dict[str, Any]]:
    pass_a = timeline["source"]["pass_a_source"]
    raw = pass_a.get("media_info_path")
    expected = pass_a.get("media_info_sha256")
    if not raw or not expected:
        raise ContractError("M10 Final pass_a_source lacks media_info provenance")

    manifest_path = resolve_path(str(raw), base=timeline_path.parent)
    verify_digest(manifest_path, str(expected), "media_info")
    manifest = load_json(manifest_path)
    source = manifest.get("source")
    if not isinstance(source, dict) or not isinstance(source.get("video"), dict):
        raise ContractError("media_info source/video is missing")
    return manifest_path, manifest


def verify_all_media(
    timeline_path: Path,
    timeline: dict[str, Any],
) -> dict[str, Path]:
    base = timeline_path.parent
    resolved_by_raw: dict[str, Path] = {}
    checked: set[tuple[str, str]] = set()

    for track in timeline["tracks"]:
        for event in track["events"]:
            raw = event.get("media_path") or event.get("asset_path")
            expected = event.get("media_sha256") or event.get("asset_sha256")
            if raw is None:
                continue
            if expected is None:
                raise ContractError(f"{event.get('id')}: physical media lacks SHA-256")
            key = (str(raw), str(expected))
            if key not in checked:
                path = resolve_path(str(raw), base=base)
                verify_digest(path, str(expected), str(event.get("id")))
                checked.add(key)
                resolved_by_raw[str(raw)] = path

    return resolved_by_raw
