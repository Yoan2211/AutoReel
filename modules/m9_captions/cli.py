import argparse
import sys

from .planner import plan_captions


def main():
    parser = argparse.ArgumentParser(description="Plan captions from M1 words and M10 Pass A chronology")
    parser.add_argument("transcript")
    parser.add_argument("timeline_draft")
    parser.add_argument("captions")
    args = parser.parse_args()
    try:
        value = plan_captions(args.transcript, args.timeline_draft, args.captions)
    except (OSError, ValueError) as exc:
        print(f"M9: {exc}", file=sys.stderr); return 1
    print(f"M9: {args.captions} ({value['summary']['caption_count']} captions)")
    return 0
