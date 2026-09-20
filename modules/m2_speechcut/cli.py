"""Standalone M2 CLI."""

import argparse
import sys

from .config import SpeechCutConfig
from .speechcut import speechcut


def main() -> int:
    parser = argparse.ArgumentParser(description="Create conservative SpeechCut decisions")
    parser.add_argument("transcript")
    parser.add_argument("cuts")
    parser.add_argument("time_map")
    parser.add_argument("--long-silence-us", type=int, default=1_200_000)
    parser.add_argument("--review-pause-us", type=int, default=850_000)
    parser.add_argument("--retained-pause-us", type=int, default=420_000)
    parser.add_argument("--review-fillers", action="store_true")
    parser.add_argument("--review-repetitions", action="store_true")
    args = parser.parse_args()
    try:
        cuts, _ = speechcut(args.transcript, args.cuts, args.time_map, SpeechCutConfig(
            long_silence_us=args.long_silence_us,
            review_pause_us=args.review_pause_us,
            retained_pause_us=args.retained_pause_us,
            auto_apply_fillers=not args.review_fillers,
            auto_apply_repetitions=not args.review_repetitions,
        ))
    except (OSError, ValueError) as exc:
        print(f"M2: {exc}", file=sys.stderr)
        return 1
    print(f"M2: {args.cuts}; {args.time_map} ({cuts['summary']['auto_applied_count']} automatic cuts)")
    return 0
