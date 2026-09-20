import argparse, sys
from .autocam import autocam
from .config import AutoCamConfig


def main():
    parser = argparse.ArgumentParser(description="Analyze kept SOURCE intervals and create a 9:16 camera plan")
    parser.add_argument("source_manifest"); parser.add_argument("smartedit_time_map"); parser.add_argument("camera_plan")
    parser.add_argument("--device", choices=("auto", "cpu", "cuda"), default="auto")
    parser.add_argument("--no-cpu-fallback", action="store_true")
    parser.add_argument("--sample-interval-us", type=int, default=250000)
    args = parser.parse_args()
    try:
        plan = autocam(args.source_manifest, args.smartedit_time_map, args.camera_plan,
                       AutoCamConfig(device=args.device, cpu_fallback=not args.no_cpu_fallback,
                                     sample_interval_us=args.sample_interval_us))
    except (OSError, ValueError) as exc:
        print(f"M4: {exc}", file=sys.stderr); return 1
    print(f"M4: {args.camera_plan} ({plan['summary']['frames_analyzed']} frames)"); return 0
