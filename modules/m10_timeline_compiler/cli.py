import argparse
import sys

from .compiler import compile_pass_a


def main():
    parser = argparse.ArgumentParser(description="Compile AutoReel Timeline Compiler Pass A")
    parser.add_argument("media_info")
    parser.add_argument("smartedit_time_map")
    parser.add_argument("edit_plan")
    parser.add_argument("camera_plan")
    parser.add_argument("visual_plan")
    parser.add_argument("sound_plan")
    parser.add_argument("music_plan")
    parser.add_argument("assets_manifest")
    parser.add_argument("timeline_draft")
    args = parser.parse_args()
    try:
        value = compile_pass_a(args.media_info, args.smartedit_time_map, args.edit_plan,
                               args.camera_plan, args.visual_plan, args.sound_plan,
                               args.music_plan, args.assets_manifest, args.timeline_draft)
    except (OSError, ValueError) as exc:
        print(f"M10 Pass A: {exc}", file=sys.stderr)
        return 1
    print(f"M10 Pass A: {args.timeline_draft} ({value['summary']['event_count']} events)")
    return 0
