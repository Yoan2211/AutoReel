from __future__ import annotations

import argparse
import json
from pathlib import Path

from .contracts import load_final_timeline
from .lua_runtime import render_runtime
from .plan import build_plan
from .srt import write_srt
from .time_conversion import parse_fps


def _next_output_dir(base: Path) -> Path:
    if not base.exists():
        return base
    index = 1
    while True:
        candidate = base.with_name(f"{base.name}_{index:03d}")
        if not candidate.exists():
            return candidate
        index += 1


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="Prepare M11 Lua build for DaVinci Resolve Free 21.0.4"
    )
    parser.add_argument("--timeline", required=True, help="M10 Final timeline.json")
    parser.add_argument(
        "--fps",
        required=True,
        help='Target Resolve FPS as an exact rational, e.g. "60000/1001"',
    )
    parser.add_argument(
        "--timeline-name",
        default="AutoReel",
        help="Base name for the new Resolve timeline",
    )
    parser.add_argument(
        "--output-dir",
        default=None,
        help="Optional output directory. Existing builds are never overwritten.",
    )
    args = parser.parse_args(argv)

    parse_fps(args.fps)
    timeline_path, timeline, timeline_hash = load_final_timeline(args.timeline)

    if args.output_dir:
        requested = Path(args.output_dir).expanduser()
        if not requested.is_absolute():
            requested = Path.cwd() / requested
        out_dir = _next_output_dir(requested.resolve())
    else:
        out_dir = _next_output_dir(timeline_path.parent / "m11_resolve_build")

    out_dir.mkdir(parents=True, exist_ok=False)
    lua_path = out_dir / "autoreel_m11_build.lua"
    srt_path = out_dir / "autoreel_m11_captions.srt"
    report_path = out_dir / "resolve_build_report.json"
    prepare_report = out_dir / "m11_prepare_report.json"

    v3 = next(track for track in timeline["tracks"] if track["id"] == "V3")
    write_srt(srt_path, v3["events"])

    plan = build_plan(
        timeline_path,
        timeline,
        timeline_hash,
        expected_fps=args.fps,
        timeline_name=args.timeline_name,
        report_path=report_path,
        srt_path=srt_path,
    )
    lua_path.write_text(render_runtime(plan), encoding="utf-8")

    prepare_value = {
        "schema_version": "1.0.0",
        "module": {"id": "M11", "version": "1.0.0"},
        "stage": "resolve_builder_prepare",
        "timeline_json_path": str(timeline_path),
        "timeline_json_sha256": timeline_hash,
        "expected_fps": args.fps,
        "lua_path": str(lua_path),
        "srt_path": str(srt_path),
        "report_path": str(report_path),
        "status": "READY",
    }
    prepare_report.write_text(
        json.dumps(prepare_value, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    print("M11 PREPARE: READY")
    print(f"Output directory : {out_dir}")
    print(f"Lua builder      : {lua_path}")
    print(f"Captions SRT     : {srt_path}")
    print(f"Expected report  : {report_path}")
    print()
    print("Dans Resolve > Workspace > Console > Lua, colle exactement :")
    print(f"dofile([[{lua_path}]])")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
