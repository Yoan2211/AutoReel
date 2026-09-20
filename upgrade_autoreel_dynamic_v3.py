from __future__ import annotations

import json
import math
import random
import shutil
import struct
import wave
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BACKUP_ROOT = ROOT / "_upgrade_backups" / ("dynamic_v3_" + datetime.now().strftime("%Y%m%d_%H%M%S"))


def backup(path: Path) -> None:
    rel = path.relative_to(ROOT)
    dst = BACKUP_ROOT / rel
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(path, dst)


def replace_once(path: Path, old: str, new: str, label: str) -> None:
    if not path.is_file():
        raise RuntimeError(f"{label}: fichier introuvable: {path}")
    text = path.read_text(encoding="utf-8")
    if new in text:
        print(f"[OK] {label}: déjà appliqué")
        return
    if old not in text:
        raise RuntimeError(f"{label}: bloc attendu introuvable")
    backup(path)
    path.write_text(text.replace(old, new, 1), encoding="utf-8")
    print(f"[OK] {label}")


def patch_m2() -> None:
    p = ROOT / "modules" / "m2_speechcut" / "config.py"
    text = p.read_text(encoding="utf-8")
    repls = {
        "long_silence_us: int = 1_200_000": "long_silence_us: int = 800_000",
        "review_pause_us: int = 850_000": "review_pause_us: int = 560_000",
        "retained_pause_us: int = 420_000": "retained_pause_us: int = 240_000",
        "filler_padding_us: int = 35_000": "filler_padding_us: int = 25_000",
        "repetition_max_gap_us: int = 450_000": "repetition_max_gap_us: int = 600_000",
        "phrase_restart_max_gap_us: int = 900_000": "phrase_restart_max_gap_us: int = 1_200_000",
    }
    changed = False
    for old, new in repls.items():
        if old in text:
            if not changed:
                backup(p)
                changed = True
            text = text.replace(old, new)
    if changed:
        p.write_text(text, encoding="utf-8")
    print("[OK] M2: pauses plus dynamiques")

    p = ROOT / "modules" / "m2_speechcut" / "analyze.py"
    old = (
        '                    "PHRASE_RESTART", words[first].start_us, words[second - 1].end_us,\n'
        '                    "REVIEW", "MEDIUM", f"Repeated phrase prefix of {length} words", ids,\n'
    )
    new = (
        '                    "PHRASE_RESTART", words[first].start_us, words[second - 1].end_us,\n'
        '                    "AUTO", "HIGH", f"Exact repeated phrase prefix of {length} words", ids,\n'
    )
    replace_once(p, old, new, "M2: reprises exactes auto-supprimées")

    p = ROOT / "modules" / "m2_speechcut" / "resolve.py"
    replace_once(
        p,
        'PRIORITY = {"IMMEDIATE_REPETITION": 30, "FILLER": 20, "LONG_SILENCE": 10}',
        'PRIORITY = {"PHRASE_RESTART": 40, "IMMEDIATE_REPETITION": 30, "FILLER": 20, "LONG_SILENCE": 10}',
        "M2: priorité des reprises",
    )


def patch_m3() -> None:
    p = ROOT / "modules" / "m3_smartedit" / "config.py"
    replace_once(
        p,
        "auto_remove_exact_duplicates: bool = False",
        "auto_remove_exact_duplicates: bool = True",
        "M3: doublons exacts automatiques",
    )

    p = ROOT / "modules" / "m3_smartedit" / "analyze.py"
    text = p.read_text(encoding="utf-8")

    if "_semantic_auto_remove" not in text:
        anchor = "\n\ndef roles(passages: list[Passage]) -> list[dict]:\n"
        helper = (
            '\n\ndef _semantic_auto_remove(left: Passage, right: Passage, score: float) -> bool:\n'
            '    # Auto-remove only very strong nearby retakes; ambiguous matches stay REVIEW.\n'
            '    return score >= 0.82 and abs(right.source_start_us - left.source_start_us) <= 20_000_000\n'
        )
        if anchor not in text:
            raise RuntimeError("M3: point d'insertion helper introuvable")
        backup(p)
        text = text.replace(anchor, helper + "\n\ndef roles(passages: list[Passage]) -> list[dict]:\n", 1)

    old = (
        '            result.append({\n'
        '                "id": f"decision{len(result):06d}", "kind": "SEMANTIC_REPETITION",\n'
        '                "disposition": "REVIEW", "confidence": "MEDIUM",\n'
    )
    new = (
        '            auto_remove = _semantic_auto_remove(left, right, score)\n'
        '            result.append({\n'
        '                "id": f"decision{len(result):06d}", "kind": "SEMANTIC_REPETITION",\n'
        '                "disposition": "AUTO_REMOVE" if auto_remove else "REVIEW",\n'
        '                "confidence": "HIGH" if auto_remove else "MEDIUM",\n'
    )
    if new not in text:
        if old not in text:
            raise RuntimeError("M3: bloc SEMANTIC_REPETITION introuvable")
        if not (BACKUP_ROOT / p.relative_to(ROOT)).exists():
            backup(p)
        text = text.replace(old, new, 1)
    p.write_text(text, encoding="utf-8")
    print("[OK] M3: retakes très similaires auto-supprimés")

    p = ROOT / "modules" / "m3_smartedit" / "smartedit.py"
    old = (
        '    auto_removals = [(item["source_start_us"], item["source_end_us"])\n'
        '                     for item in edit_decisions if item["disposition"] == "AUTO_REMOVE"]\n'
    )
    new = (
        '    auto_removals = sorted(set(\n'
        '        (item["source_start_us"], item["source_end_us"])\n'
        '        for item in edit_decisions if item["disposition"] == "AUTO_REMOVE"\n'
        '    ))\n'
    )
    replace_once(p, old, new, "M3: suppressions dédupliquées")


def patch_m5() -> None:
    p = ROOT / "modules" / "m5_visual_planner" / "concepts.py"
    text = p.read_text(encoding="utf-8")
    old = 'ILLUSTRATION = frozenset({"exemple", "imagine", "visualise", "concept", "mécanisme", "processus", "fonctionne", "architecture", "cycle"})\n'
    if "MEDICAL_SYMPTOM" not in text:
        new = old + (
            'MEDICAL_SYMPTOM = frozenset({\n'
            '    "fatigue", "fatigué", "fatiguée", "essoufflement", "essoufflé", "vertige", "vertiges",\n'
            '    "palpitation", "palpitations", "pâle", "pale", "peau", "muqueuse", "muqueuses",\n'
            '})\n'
            'MEDICAL_EXPLAIN = frozenset({\n'
            '    "anémie", "anemie", "sang", "hémoglobine", "hemoglobine", "oxygène", "oxygene",\n'
            '    "globule", "globules", "fer", "carence", "prise", "dosage",\n'
            '})\n'
        )
        if old not in text:
            raise RuntimeError("M5: lexique principal introuvable")
        backup(p)
        text = text.replace(old, new, 1)

    old_detect = (
        '    elif word_set & BROLL:\n'
        '        media_type, score, signal = "BROLL", .83, "concrete action or environment"\n'
        '    elif word_set & PHOTO:\n'
        '        media_type, score, signal = "PHOTO", .8, "specific person, place or object"\n'
    )
    new_detect = (
        '    elif word_set & BROLL:\n'
        '        media_type, score, signal = "BROLL", .83, "concrete action or environment"\n'
        '    elif word_set & MEDICAL_SYMPTOM:\n'
        '        media_type, score, signal = "PHOTO", .88, "explicit medical symptom suited to a visual cutaway"\n'
        '    elif word_set & MEDICAL_EXPLAIN:\n'
        '        media_type, score, signal = "ILLUSTRATION", .90, "medical mechanism or diagnostic concept"\n'
        '    elif word_set & PHOTO:\n'
        '        media_type, score, signal = "PHOTO", .8, "specific person, place or object"\n'
    )
    if new_detect not in text:
        if old_detect not in text:
            raise RuntimeError("M5: bloc de détection introuvable")
        if not (BACKUP_ROOT / p.relative_to(ROOT)).exists():
            backup(p)
        text = text.replace(old_detect, new_detect, 1)

    p.write_text(text, encoding="utf-8")
    print("[OK] M5: concepts médicaux reconnus")


def patch_m8() -> None:
    p = ROOT / "modules" / "m8_music" / "context.py"
    old = '    ("clean_modern_medical", {"santé", "medical", "médical", "médecin", "patient", "soin", "science"}),\n'
    new = (
        '    ("clean_modern_medical", {\n'
        '        "santé", "medical", "médical", "médecin", "patient", "soin", "science",\n'
        '        "anémie", "anemie", "sang", "hémoglobine", "hemoglobine", "oxygène", "oxygene",\n'
        '        "fatigue", "essoufflement", "vertige", "vertiges", "palpitations", "fer",\n'
        '    }),\n'
    )
    replace_once(p, old, new, "M8: contexte médical enrichi")


def patch_m9() -> None:
    p = ROOT / "modules" / "m9_captions" / "segmentation.py"
    old = (
        'def _should_break(group, current, following, config):\n'
        '    if len(group) >= config.maximum_words:\n'
        '        return True\n'
    )
    new = (
        'def _should_break(group, current, following, config):\n'
        '    # Ne pas couper "peut" + "-être" ni "d" + "\'habitude".\n'
        '    if following is not None:\n'
        '        next_text = following.text.lstrip()\n'
        '        current_text = current.text.rstrip()\n'
        '        if next_text.startswith(("-", "\'", "’")) or current_text.endswith(("-", "\'", "’")):\n'
        '            return False\n'
        '    if len(group) >= config.maximum_words:\n'
        '        return True\n'
    )
    replace_once(p, old, new, "M9: mots composés non coupés")


def patch_gui() -> None:
    p = ROOT / "autoreel_gui.py"
    if not p.is_file():
        print("[WARN] autoreel_gui.py introuvable")
        return

    text = p.read_text(encoding="utf-8")
    changed = False

    marker = '"-m", "modules.m3_smartedit"'
    if marker in text and "--auto-remove-exact-duplicates" not in text:
        pos = text.find(marker)
        old = '                str(p / "time_map_smartedit.json"),\n            ]))\n'
        idx = text.find(old, pos)
        if idx >= 0:
            backup(p)
            changed = True
            new = (
                '                str(p / "time_map_smartedit.json"),\n'
                '                "--auto-remove-exact-duplicates",\n'
                '            ]))\n'
            )
            text = text[:idx] + new + text[idx + len(old):]

    old_worker = (
        '                self._run_subprocess(command, "M11")\n'
        '                self.queue.put(("m11_done", None))\n'
    )
    new_worker = (
        '                self._run_subprocess(command, "M11")\n'
        '                enhancer = ROOT / "tools" / "m11_dynamic_postprocess.py"\n'
        '                if enhancer.is_file():\n'
        '                    self._run_subprocess([str(self.python_exe), str(enhancer), str(self.project_dir)], "M11")\n'
        '                self.queue.put(("m11_done", None))\n'
    )
    if "m11_dynamic_postprocess.py" not in text and old_worker in text:
        if not changed:
            backup(p)
            changed = True
        text = text.replace(old_worker, new_worker, 1)

    if changed:
        p.write_text(text, encoding="utf-8")
        print("[OK] GUI: mode dynamique branché")
    else:
        print("[OK] GUI: aucun changement supplémentaire")


def write_pcm_stereo(path: Path, samples, rate=48000):
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(rate)
        frames = bytearray()
        for x in samples:
            x = max(-1.0, min(1.0, x))
            v = int(x * 32767)
            frames += struct.pack("<hh", v, v)
        w.writeframes(bytes(frames))


def generate_assets() -> None:
    rate = 48000
    sfx = ROOT / "assets" / "sfx"
    sfx.mkdir(parents=True, exist_ok=True)

    def tone(duration, f0, f1, noise, amp):
        n = int(duration * rate)
        phase = 0.0
        rng = random.Random(42)
        data = []
        for i in range(n):
            t = i / max(1, n - 1)
            f = f0 + (f1 - f0) * t
            phase += 2 * math.pi * f / rate
            env = (1 - t) ** 2.4
            data.append(math.sin(phase) * amp * env + (rng.random() * 2 - 1) * noise * env)
        return data

    specs = {
        "soft_impact.wav": tone(0.38, 130, 75, 0.02, 0.48),
        "pop.wav": tone(0.20, 620, 300, 0.006, 0.38),
        "click.wav": tone(0.09, 1800, 900, 0.008, 0.24),
        "whoosh.wav": tone(0.55, 170, 760, 0.045, 0.24),
        "swoosh.wav": tone(0.48, 210, 940, 0.04, 0.22),
        "accent.wav": tone(0.28, 420, 180, 0.009, 0.32),
    }
    for name, data in specs.items():
        path = sfx / name
        if not path.exists():
            write_pcm_stereo(path, data, rate)
        path.with_name(path.name + ".asset.json").write_text(
            json.dumps(
                {"asset_type": "SFX", "tags": [path.stem.upper(), path.stem, "subtle", "clean"]},
                ensure_ascii=False, indent=2,
            ) + "\n",
            encoding="utf-8",
        )
    print("[OK] Assets: SFX générés")

    music = ROOT / "assets" / "music" / "clean_modern_medical_neutral_low.wav"
    if not music.exists():
        music.parent.mkdir(parents=True, exist_ok=True)
        duration = 120
        freqs = [110.0, 164.81, 220.0, 329.63]
        phases = [0.0] * len(freqs)
        rng = random.Random(20260920)
        with wave.open(str(music), "wb") as w:
            w.setnchannels(2)
            w.setsampwidth(2)
            w.setframerate(rate)
            total = duration * rate
            chunk = 4096
            done = 0
            while done < total:
                count = min(chunk, total - done)
                frames = bytearray()
                for j in range(count):
                    t = (done + j) / rate
                    mod = 0.72 + 0.18 * math.sin(2 * math.pi * t / 13.0)
                    val = 0.0
                    for k, f in enumerate(freqs):
                        phases[k] += 2 * math.pi * f / rate
                        val += math.sin(phases[k]) * (0.032 / (k + 1))
                    val = val * mod + (rng.random() * 2 - 1) * 0.0012
                    frames += struct.pack("<hh", int(val * 32767), int(val * 0.97 * 32767))
                w.writeframes(bytes(frames))
                done += count

    music.with_name(music.name + ".asset.json").write_text(
        json.dumps(
            {
                "asset_type": "MUSIC",
                "tags": [
                    "clean_modern_medical", "clean_modern_neutral", "clean_modern_educational",
                    "LOW", "low", "subtle", "medical", "health", "anemia",
                ],
            },
            ensure_ascii=False, indent=2,
        ) + "\n",
        encoding="utf-8",
    )
    print("[OK] Assets: bed musical original généré")


def main():
    print("=" * 72)
    print("AUTOREEL DYNAMIC V3 - UPGRADE")
    print("=" * 72)
    try:
        patch_m2()
        patch_m3()
        patch_m5()
        patch_m8()
        patch_m9()
        patch_gui()
        generate_assets()
    except Exception as exc:
        print(f"\nERREUR: {exc}")
        print(f"Sauvegardes: {BACKUP_ROOT}")
        input("\nAppuie sur Entrée pour fermer...")
        raise SystemExit(1)

    print("\nUpgrade installé.")
    print("Sauvegardes:", BACKUP_ROOT)
    print("\nMaintenant lance AutoReel_REBUILD_DYNAMIC_V3.bat")
    input("\nAppuie sur Entrée pour fermer...")


if __name__ == "__main__":
    main()
