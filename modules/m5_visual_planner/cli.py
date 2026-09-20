import argparse
import sys

from .config import VisualPlannerConfig
from .planner import plan_visuals


def main():
    parser = argparse.ArgumentParser(description="Plan useful visual asset requests without resolving assets")
    parser.add_argument("edit_plan")
    parser.add_argument("transcript")
    parser.add_argument("smartedit_time_map")
    parser.add_argument("visual_plan")
    parser.add_argument("--camera-plan")
    parser.add_argument("--minimum-gap-us", type=int, default=3_500_000)
    parser.add_argument("--maximum-visuals-per-section", type=int, default=2)
    args = parser.parse_args()
    try:
        plan = plan_visuals(args.edit_plan, args.transcript, args.smartedit_time_map,
                            args.visual_plan, args.camera_plan,
                            VisualPlannerConfig(minimum_gap_us=args.minimum_gap_us,
                                                maximum_visuals_per_section=args.maximum_visuals_per_section))
    except (OSError, ValueError) as exc:
        print(f"M5: {exc}", file=sys.stderr)
        return 1
    print(f"M5: {args.visual_plan} ({plan['summary']['selected_count']} visuals selected)")
    return 0
