from __future__ import annotations
import argparse
from .motion import build_motion_package

def main() -> int:
    p = argparse.ArgumentParser(description="AutoReel M5B Motion Designer")
    p.add_argument("transcript")
    p.add_argument("edit_plan")
    p.add_argument("time_map")
    p.add_argument("visual_plan")
    p.add_argument("output_plan")
    p.add_argument("render_dir")
    p.add_argument("--fps", type=float, default=30.0)
    p.add_argument("--max-events", type=int, default=8)
    a = p.parse_args()
    plan = build_motion_package(
        a.transcript, a.edit_plan, a.time_map, a.visual_plan,
        a.output_plan, a.render_dir, a.fps, a.max_events
    )
    print(f"M5B: {a.output_plan} ({plan['summary']['selected_count']} animations)")
    return 0
