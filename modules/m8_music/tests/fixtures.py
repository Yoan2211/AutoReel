import json

from modules.m7_sounddesign.planner import plan_sounds
from modules.m7_sounddesign.tests.fixtures import make_chain


def make_music_chain(root, sentences, **kwargs):
    sound_inputs = make_chain(root, sentences, **kwargs)
    plan_sounds(*sound_inputs)
    transcript, edit, visual, _camera, time_map, sound = sound_inputs
    return transcript, edit, time_map, visual, sound, root / "music-plan.json"


def move_first_active_sfx(sound_path, cut_time_us, source_time_us=None):
    value = json.loads(sound_path.read_text(encoding="utf-8"))
    item = next(decision for decision in value["decisions"] if decision["status"] != "NONE")
    item["cut_time_us"] = cut_time_us
    item["source_time_us"] = cut_time_us if source_time_us is None else source_time_us
    sound_path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
