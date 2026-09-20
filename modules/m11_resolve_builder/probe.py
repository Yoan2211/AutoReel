from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .bridge import BridgeSession, connect_bridge, read_bridge_config
from .config import ResolveBridgeConfig
from .errors import ResolveBuilderError


def _cap(session: BridgeSession, obj: Any, methods: list[str]) -> dict[str, bool]:
    return {name: session.has_method(obj, name) for name in methods}


def _first_timeline_item(session: BridgeSession, timeline: Any, kind: str) -> Any:
    if timeline is None or not session.has_method(timeline, "GetItemListInTrack"):
        return None
    try:
        values = timeline.GetItemListInTrack(kind, 1) or []
        return values[0] if values else None
    except Exception:
        return None


def collect_capabilities(session: BridgeSession) -> dict:
    resolve = session.resolve
    health = session.health()

    project_manager = session.safe_call(resolve, "GetProjectManager")
    project = session.safe_call(project_manager, "GetCurrentProject")
    media_pool = session.safe_call(project, "GetMediaPool")
    current_timeline = session.safe_call(project, "GetCurrentTimeline")

    video_item = _first_timeline_item(session, current_timeline, "video")
    audio_item = _first_timeline_item(session, current_timeline, "audio")

    result = {
        "probe_version": "1.0.0",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "bridge": {
            "health": health,
            "config": read_bridge_config(session.config),
        },
        "project": {
            "open": project is not None,
            "name": session.safe_call(project, "GetName"),
            "timeline_count": session.safe_call(project, "GetTimelineCount"),
            "current_timeline": session.safe_call(current_timeline, "GetName"),
        },
        "capabilities": {
            "resolve": _cap(session, resolve, [
                "GetProjectManager", "GetProductName", "GetVersionString",
                "GetCurrentPage", "OpenPage"
            ]),
            "project_manager": _cap(session, project_manager, [
                "GetCurrentProject"
            ]),
            "project": _cap(session, project, [
                "GetName", "GetTimelineCount", "GetTimelineByIndex",
                "GetCurrentTimeline", "SetCurrentTimeline", "GetMediaPool",
                "GetSetting", "SetSetting"
            ]),
            "media_pool": _cap(session, media_pool, [
                "GetRootFolder", "ImportMedia", "CreateEmptyTimeline",
                "CreateTimelineFromClips", "AppendToTimeline"
            ]),
            "timeline": _cap(session, current_timeline, [
                "GetName", "GetStartFrame", "GetEndFrame", "GetTrackCount",
                "AddTrack", "GetItemListInTrack", "GetSetting", "SetSetting",
                "AddMarker"
            ]),
            "video_timeline_item": _cap(session, video_item, [
                "GetStart", "GetEnd", "GetDuration", "GetProperty",
                "SetProperty", "AddMarker"
            ]),
            "audio_timeline_item": _cap(session, audio_item, [
                "GetStart", "GetEnd", "GetDuration", "GetProperty",
                "SetProperty", "AddMarker"
            ]),
        },
        "notes": [
            "This probe performs read-only API calls only.",
            "No timeline is created or modified by phase 1.",
            "A false capability can mean either unsupported by this Resolve build or unavailable because no suitable live object exists yet."
        ],
    }
    return result


def write_exclusive(path: Path, value: dict) -> None:
    path = path.resolve()
    if path.exists() or path.is_symlink():
        raise FileExistsError(f"Refusing to overwrite existing probe output: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="AutoReel M11 Resolve Free capability probe")
    parser.add_argument(
        "--output",
        default="resolve_capabilities.json",
        help="New JSON file to create (default: resolve_capabilities.json)",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=8.0,
        help="Bridge timeout in seconds",
    )
    args = parser.parse_args(argv)

    config = ResolveBridgeConfig.default()
    config = ResolveBridgeConfig(
        install_root=config.install_root,
        config_path=config.config_path,
        timeout_seconds=args.timeout,
    )

    try:
        session = connect_bridge(config)
        value = collect_capabilities(session)
        write_exclusive(Path(args.output), value)
    except ResolveBuilderError as exc:
        print(f"M11 PROBE ERROR: {exc}")
        return 2
    except FileExistsError as exc:
        print(f"M11 PROBE ERROR: {exc}")
        return 3

    print(json.dumps(value, indent=2, ensure_ascii=False))
    print(f"\nWritten: {Path(args.output).resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
