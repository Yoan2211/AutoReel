import argparse
import sys

from .config import SmartEditConfig
from .smartedit import smartedit


def main() -> int:
    parser = argparse.ArgumentParser(description="Build a conservative semantic edit plan")
    parser.add_argument("transcript")
    parser.add_argument("cuts")
    parser.add_argument("speechcut_time_map")
    parser.add_argument("edit_plan")
    parser.add_argument("smartedit_time_map")
    parser.add_argument("--auto-remove-exact-duplicates", action="store_true")
    args = parser.parse_args()
    try:
        plan, _ = smartedit(args.transcript, args.cuts, args.speechcut_time_map,
                            args.edit_plan, args.smartedit_time_map,
                            SmartEditConfig(auto_remove_exact_duplicates=args.auto_remove_exact_duplicates))
    except (OSError, ValueError) as exc:
        print(f"M3: {exc}", file=sys.stderr)
        return 1
    print(f"M3: {args.edit_plan}; {args.smartedit_time_map} ({len(plan['decisions'])} decisions)")
    return 0
