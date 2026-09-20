from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
MODELS = ROOT / "models" / "faster-whisper"


def ok(label):
    print(f"[OK] {label}")


def warn(label):
    print(f"[A FAIRE] {label}")


def find_complete_small():
    required = ("model.bin", "config.json", "tokenizer.json")
    for root in MODELS.rglob("models--Systran--faster-whisper-small"):
        snapshots = root / "snapshots"
        if not snapshots.is_dir():
            continue
        for snap in snapshots.iterdir():
            if snap.is_dir() and all((snap / name).is_file() and (snap / name).stat().st_size > 0 for name in required):
                return snap
    return None


def main():
    print("=" * 64)
    print("AUTOREEL - PREPARATION INITIALE")
    print("=" * 64)

    failures = []

    # Core executables
    for exe in ("ffmpeg", "ffprobe"):
        path = shutil.which(exe)
        if path:
            ok(f"{exe}: {path}")
        else:
            failures.append(f"{exe} introuvable")
            warn(f"{exe} introuvable dans PATH")

    # Python packages
    packages = [
        ("jsonschema", "jsonschema"),
        ("faster-whisper", "faster_whisper"),
        ("OpenCV", "cv2"),
        ("NumPy", "numpy"),
    ]
    for label, module in packages:
        try:
            __import__(module)
            ok(label)
        except Exception as exc:
            failures.append(f"{label}: {exc}")
            warn(f"{label} non disponible")

    # OpenCV local detectors
    try:
        import cv2
        cascade = Path(cv2.data.haarcascades) / "haarcascade_frontalface_default.xml"
        if cascade.is_file():
            ok("Détecteur visage OpenCV Haar (inclus localement)")
        else:
            failures.append("Cascade Haar OpenCV manquante")
            warn("Cascade Haar OpenCV manquante")
    except Exception:
        pass

    # Current external ML model set
    small = find_complete_small()
    if small:
        ok(f"Whisper small déjà téléchargé: {small}")
    else:
        warn("Whisper small n'est pas complet.")
        answer = input("Télécharger Whisper small maintenant ? [O/n] ").strip().lower()
        if answer in ("", "o", "oui", "y", "yes"):
            os.environ.setdefault("HF_HUB_DISABLE_XET", "1")
            os.environ.setdefault("HF_HUB_DOWNLOAD_TIMEOUT", "120")
            os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")
            MODELS.mkdir(parents=True, exist_ok=True)
            try:
                from faster_whisper.utils import download_model
                print("\nTéléchargement de Whisper small...")
                model_path = download_model("small", cache_dir=str(MODELS))
                print(f"\n[OK] Whisper small: {model_path}")
                small = find_complete_small()
                if not small:
                    failures.append("Whisper small téléchargé mais snapshot incomplet")
            except Exception as exc:
                failures.append(f"Téléchargement Whisper small: {exc}")
                print(f"\n[ERREUR] {exc}")

    print("\n" + "-" * 64)
    if failures:
        print("Préparation incomplète :")
        for item in failures:
            print(" -", item)
    else:
        print("AutoReel est prêt : dépendances et modèles requis sont disponibles.")
        print("Modèles externes requis actuellement : Whisper small.")
        print("M4 AutoCam utilise les détecteurs OpenCV locaux, sans modèle à télécharger.")
    print("-" * 64)
    input("\nAppuie sur Entrée pour fermer...")


if __name__ == "__main__":
    main()
