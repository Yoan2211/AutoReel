import argparse
import sys

from .config import SoundDesignConfig
from .planner import plan_sounds


def main():
    parser = argparse.ArgumentParser(description="Plan subtle SFX requests without resolving audio assets")
    parser.add_argument("transcript")
    parser.add_argument("edit_plan")
    parser.add_argument("visual_plan")
    parser.add_argument("camera_plan")
    parser.add_argument("smartedit_time_map")
    parser.add_argument("sound_plan")
    parser.add_argument("--minimum-gap-us", type=int, default=3_000_000)
    parser.add_argument("--maximum-sfx-per-minute", type=int, default=8)
    args = parser.parse_args()
    try:
        plan = plan_sounds(args.transcript, args.edit_plan, args.visual_plan, args.camera_plan,
                           args.smartedit_time_map, args.sound_plan,
                           SoundDesignConfig(minimum_gap_us=args.minimum_gap_us,
                                             maximum_sfx_per_window=args.maximum_sfx_per_minute))
    except (OSError, ValueError) as exc:
        print(f"M7: {exc}", file=sys.stderr)
        return 1
    print(f"M7: {args.sound_plan} ({plan['summary']['proposed_count']} proposed SFX)")
    return 0
