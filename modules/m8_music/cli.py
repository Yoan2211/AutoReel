import argparse
import sys

from .config import MusicPlannerConfig
from .planner import plan_music


def main():
    parser = argparse.ArgumentParser(description="Plan a voice-first music bed without resolving audio assets")
    parser.add_argument("transcript")
    parser.add_argument("edit_plan")
    parser.add_argument("smartedit_time_map")
    parser.add_argument("visual_plan")
    parser.add_argument("sound_plan")
    parser.add_argument("music_plan")
    parser.add_argument("--speech-gain-db", type=float, default=-28.0)
    parser.add_argument("--no-speech-gain-db", type=float, default=-21.0)
    args = parser.parse_args()
    try:
        plan = plan_music(args.transcript, args.edit_plan, args.smartedit_time_map,
                          args.visual_plan, args.sound_plan, args.music_plan,
                          MusicPlannerConfig(speech_gain_db=args.speech_gain_db,
                                             no_speech_gain_db=args.no_speech_gain_db))
    except (OSError, ValueError) as exc:
        print(f"M8: {exc}", file=sys.stderr)
        return 1
    print(f"M8: {args.music_plan} ({plan['decision']['status']})")
    return 0
