import argparse
import sys

from .config import AssetManagerConfig
from .manager import resolve_assets


def main():
    parser = argparse.ArgumentParser(description="Resolve planned requests against a validated local asset library")
    parser.add_argument("visual_plan")
    parser.add_argument("sound_plan")
    parser.add_argument("music_plan")
    parser.add_argument("asset_library")
    parser.add_argument("assets_manifest")
    parser.add_argument("--project-root")
    parser.add_argument("--ffprobe", default="ffprobe")
    args = parser.parse_args()
    try:
        manifest = resolve_assets(args.visual_plan, args.sound_plan, args.music_plan,
                                  args.asset_library, args.assets_manifest,
                                  AssetManagerConfig(ffprobe_path=args.ffprobe),
                                  project_root_path=args.project_root)
    except (OSError, ValueError) as exc:
        print(f"M6: {exc}", file=sys.stderr)
        return 1
    print(f"M6: {args.assets_manifest} ({manifest['summary']['resolved_count']} resolved)")
    return 0
