from __future__ import annotations

import os
import shutil
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PROJECTS = ROOT / "projects"

ARTIFACTS = [
    "cuts.json",
    "time_map_speechcut.json",
    "edit_plan.json",
    "time_map_smartedit.json",
    "camera_plan.json",
    "visual_plan.json",
    "sound_plan.json",
    "music_plan.json",
    "assets_manifest.json",
    "timeline_draft.json",
    "captions.json",
    "timeline.json",
]


def main():
    default = "anemie" if (PROJECTS / "anemie").is_dir() else ""
    name = input(f"Projet [{default or 'nom'}] : ").strip() or default
    if not name:
        raise SystemExit("Aucun projet.")
    project = PROJECTS / name
    if not project.is_dir():
        raise SystemExit(f"Projet introuvable: {project}")
    if not (project / "source.json").is_file() or not (project / "transcript.json").is_file():
        raise SystemExit("source.json et transcript.json sont nécessaires.")

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = project / ("_backup_before_dynamic_v3_" + stamp)
    backup.mkdir()

    count = 0
    for filename in ARTIFACTS:
        src = project / filename
        if src.exists():
            shutil.move(str(src), str(backup / filename))
            count += 1

    for folder in project.glob("m11_resolve_build*"):
        if folder.is_dir() and not folder.name.startswith("_backup"):
            shutil.move(str(folder), str(backup / folder.name))
            count += 1

    print(f"\nSauvegarde: {backup}")
    print(f"{count} ancien(s) artefact(s) déplacé(s).")
    print("source.json + transcript.json conservés.")
    print("La GUI va reprendre à M2.")

    launcher = ROOT / "AutoReel_GUI.bat"
    if launcher.is_file():
        os.startfile(launcher)
    else:
        print("Relance manuellement AutoReel_GUI.bat.")

    input("\nAppuie sur Entrée pour fermer...")


if __name__ == "__main__":
    main()
