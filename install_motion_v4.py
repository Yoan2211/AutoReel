from __future__ import annotations
import importlib.util, shutil, subprocess, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent

def main():
    if importlib.util.find_spec("PIL") is None:
        print("[SETUP] Installation Pillow...")
        subprocess.run([sys.executable,"-m","pip","install","Pillow>=10,<12"],check=True)

    gui=ROOT/"autoreel_gui.py"
    if not gui.is_file():
        raise SystemExit("autoreel_gui.py introuvable")
    text=gui.read_text(encoding="utf-8"); original=text

    if '"M5B": ("motion_plan.json",),' not in text:
        text=text.replace('    "M5": ("visual_plan.json",),\n','    "M5": ("visual_plan.json",),\n    "M5B": ("motion_plan.json",),\n',1)
    if '"M5B": "Animations graphiques",' not in text:
        text=text.replace('    "M5": "Planification des visuels",\n','    "M5": "Planification des visuels",\n    "M5B": "Animations graphiques",\n',1)
    order_start=text.find("PIPELINE_ORDER")
    order_end=text.find("MODULE_LABELS")
    if order_start>=0 and '"M5B"' not in text[order_start:order_end]:
        text=text.replace('    "M0", "M1", "M2", "M3", "M4", "M5",\n','    "M0", "M1", "M2", "M3", "M4", "M5", "M5B",\n',1)
    text=text.replace(
        '("style", "Habillage", "Visuels, son et musique", ("M5", "M7", "M8", "M6")),',
        '("style", "Habillage", "Visuels, animations, son et musique", ("M5", "M5B", "M7", "M8", "M6")),'
    )

    if 'modules.m5b_motion_designer' not in text:
        marker='        if not self.module_complete("M7"):\n'
        block=(
            '        if not self.module_complete("M5B"):\n'
            '            commands.append(("M5B", [\n'
            '                py, "-m", "modules.m5b_motion_designer",\n'
            '                str(p / "transcript.json"),\n'
            '                str(p / "edit_plan.json"),\n'
            '                str(p / "time_map_smartedit.json"),\n'
            '                str(p / "visual_plan.json"),\n'
            '                str(p / "motion_plan.json"),\n'
            '                str(p / "motion_assets"),\n'
            '                "--fps", "30", "--max-events", "8",\n'
            '            ]))\n\n'
        )
        if marker not in text: raise RuntimeError("Point insertion M5B introuvable")
        text=text.replace(marker,block+marker,1)

    if "m11_motion_postprocess.py" not in text:
        marker='                self.queue.put(("m11_done", None))\n'
        block=(
            '                motion_enhancer = ROOT / "tools" / "m11_motion_postprocess.py"\n'
            '                if motion_enhancer.is_file():\n'
            '                    self._run_subprocess([str(self.python_exe), str(motion_enhancer), str(self.project_dir)], "M11")\n'
        )
        if marker not in text: raise RuntimeError("Point insertion M11 motion introuvable")
        text=text.replace(marker,block+marker,1)

    if text!=original:
        backup=gui.with_suffix(".py.before_motion_v4")
        if not backup.exists(): shutil.copy2(gui,backup)
        gui.write_text(text,encoding="utf-8")
    print("[OK] Motion V4 installé et GUI branchée")
    input("Appuie sur Entrée pour fermer...")

if __name__=="__main__": main()
