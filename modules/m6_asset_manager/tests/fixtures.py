from modules.m8_music.tests.fixtures import make_music_chain
from modules.m8_music.planner import plan_music


LONG = ["Les ventes atteignent 42 pourcent cette année.",
        "Le graphique compare 18 pourcent de progression.",
        "La stratégie du marché confirme 30 pourcent."]


def make_inputs(root, sentences=None, **kwargs):
    chain = make_music_chain(root / "plans", LONG if sentences is None else sentences,
                             spacing_us=kwargs.pop("spacing_us", 8_000_000), **kwargs)
    transcript, edit, time_map, visual, sound, music = chain
    plan_music(*chain)
    library = root / "assets"
    library.mkdir(parents=True, exist_ok=True)
    return visual, sound, music, library, root / "assets_manifest.json"


class FakeProbe:
    def __init__(self, invalid_names=()):
        self.invalid_names = set(invalid_names)
        self.calls = []

    def probe(self, path, asset_type):
        self.calls.append(path.name)
        if path.name in self.invalid_names:
            raise ValueError("fixture invalid media")
        audio = asset_type in {"SFX", "MUSIC"}
        video = asset_type == "BROLL"
        return {"media_kind": "AUDIO" if audio else "VIDEO" if video else "IMAGE",
                "format": path.suffix.lstrip("."), "codec": "fixture",
                "duration_us": 2_000_000 if audio or video else None,
                "width": 1920 if not audio else None, "height": 1080 if not audio else None,
                "sample_rate_hz": 48_000 if audio else None, "channels": 2 if audio else None,
                "loudness_lufs": None}


def add_asset(library, relative, content=b"valid-local-asset", sidecar=None):
    path = library / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
    if sidecar is not None:
        import json
        path.with_suffix(path.suffix + ".asset.json").write_text(
            json.dumps(sidecar, ensure_ascii=False), encoding="utf-8")
    return path
