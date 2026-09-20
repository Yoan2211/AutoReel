import argparse
import sys

from .final_compiler import compile_final


def main():
    parser = argparse.ArgumentParser(description="Compile AutoReel M10 Final from Pass A and M9 captions")
    parser.add_argument("timeline_draft")
    parser.add_argument("captions")
    parser.add_argument("timeline")
    args = parser.parse_args()
    try:
        value = compile_final(args.timeline_draft, args.captions, args.timeline)
    except (OSError, ValueError) as exc:
        print(f"M10 Final: {exc}", file=sys.stderr); return 1
    print(f"M10 Final: {args.timeline} ({value['summary']['caption_event_count']} captions)")
    return 0
