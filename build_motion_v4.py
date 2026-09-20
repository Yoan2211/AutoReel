from __future__ import annotations
import os, shutil, subprocess, sys
from datetime import datetime
from pathlib import Path
ROOT=Path(__file__).resolve().parent

def main():
    project=ROOT/"projects"/"anemie"
    if not project.is_dir():
        name=input("Nom du projet: ").strip(); project=ROOT/"projects"/name
    req=["transcript.json","edit_plan.json","time_map_smartedit.json","visual_plan.json"]
    miss=[x for x in req if not (project/x).is_file()]
    if miss: raise SystemExit("Manque: "+", ".join(miss))
    for target in [project/"motion_plan.json", project/"motion_assets"]:
        if target.exists():
            backup=project/("_backup_motion_v4_"+datetime.now().strftime("%Y%m%d_%H%M%S"))
            backup.mkdir(exist_ok=True)
            shutil.move(str(target),str(backup/target.name))
    cmd=[sys.executable,"-m","modules.m5b_motion_designer",
         str(project/"transcript.json"),str(project/"edit_plan.json"),
         str(project/"time_map_smartedit.json"),str(project/"visual_plan.json"),
         str(project/"motion_plan.json"),str(project/"motion_assets"),
         "--fps","30","--max-events","8"]
    subprocess.run(cmd,cwd=ROOT,check=True)
    for folder in list(project.glob("m11_resolve_build*")):
        if folder.is_dir():
            dst=project/("_backup_m11_motion_"+datetime.now().strftime("%Y%m%d_%H%M%S"))
            shutil.move(str(folder),str(dst)); break
    launcher=ROOT/"AutoReel_GUI.bat"
    if launcher.is_file(): os.startfile(launcher)
    print("\nAnimations créées. Dans la GUI, clique sur « Préparer pour DaVinci Resolve ».")
    input("Appuie sur Entrée pour fermer...")

if __name__=="__main__": main()
