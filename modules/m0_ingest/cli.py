"""Independent M0 command line entry point."""

import argparse
import sys

from .ingest import IngestConfig, IngestError, ingest


def main() -> int:
    parser = argparse.ArgumentParser(description="Reference original video in an AutoReel manifest")
    parser.add_argument("source")
    parser.add_argument("manifest")
    parser.add_argument("--ffprobe", default="ffprobe")
    parser.add_argument("--timeout-s", type=int, default=60)
    args = parser.parse_args()
    try:
        result = ingest(args.source, args.manifest, IngestConfig(args.ffprobe, args.timeout_s))
    except (OSError, ValueError) as exc:
        print(f"M0: {exc}", file=sys.stderr)
        return 1
    print(f"M0: {args.manifest}")
    for warning in result["warnings"]:
        print(f"Warning: {warning}", file=sys.stderr)
    return 0
