# AutoReel

Pipeline modulaire de préparation de vidéos courtes pour DaVinci Resolve.
**M0 à M9 et M10 Timeline Compiler Pass A v1.0.0 sont acceptés. M10 Timeline Compiler Final v1.0.0 est implémenté et attend sa validation utilisateur.**
Voir [les règles](AGENTS.md), [le contrat M0](modules/m0_ingest/README.md)
[le contrat M1](modules/m1_transcription/README.md), [le backlog](docs/BACKLOG.md)
et [l'état des modules](docs/STATUS.md).

## Installation cible (PowerShell, Python 3.11)

Installer Python 3.11 et FFmpeg/FFprobe et rendre les exécutables accessibles.
Aucune dépendance Python tierce n'est nécessaire à l'exécution de M0.

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[test]"
.\.venv\Scripts\python.exe -m modules.m0_ingest "D:\Videos\source.mov" "projects\demo\source.json"
.\.venv\Scripts\python.exe -m unittest discover -v
```

Un FFprobe hors PATH peut être passé via `--ffprobe "C:\ffmpeg\bin\ffprobe.exe"`.
Le test d'intégration réel est ignoré explicitement si FFmpeg/FFprobe manquent.

## Dossiers

- `core/` : contrat JSON et conversions temporelles partagées.
- `modules/m0_ingest/` : API, CLI, lecture FFprobe, normalisation, tests.
- `modules/m1_transcription/` : transcription locale, audio temporaire, mots en temps SOURCE, tests.
- `modules/m2_speechcut/` : décisions de coupe SOURCE et time map SOURCE→CUT, sans média dérivé.
- `modules/m3_smartedit/` : plan sémantique justifié et mapping SmartEdit SOURCE→CUT.
- `modules/m4_autocam/` : détection, suivi et cadrage 9:16 sur les intervalles SOURCE conservés.
- `modules/m5_visual_planner/` : demandes visuelles SOURCE/CUT prudentes, sans recherche d'assets.
- `modules/m7_sounddesign/` : propositions de SFX sobres avec décisions `NONE`, sans fichiers audio.
- `modules/m8_music/` : lit musical stable, ducking vocal et demande d'asset sans morceau concret.
- `modules/m6_asset_manager/` : résolution locale, validation et manifest d'assets stables.
- `modules/m10_timeline_compiler/` : compilation pure de la timeline Pass A, sans décision éditoriale.
- `modules/m9_captions/` : captions SOURCE/CUT/TIMELINE depuis les mots M1 et la chronologie Pass A.
- `modules/m10_timeline_compiler/final_compiler.py` : fusion finale immuable de Pass A et des captions M9.
- `models/`, `assets/`, `projects/` : données locales non versionnées.
- `tests/` : tests transversaux du socle partagé.
- `tools/` : emplacement réservé aux outils auxiliaires.
- `docs/` : suivi de validation.

M11 et les modules suivants, le rendu et l'accès à Resolve ne sont pas implémentés.

## AutoCam M4

```powershell
.\.venv\Scripts\python.exe -m pip install -e ".[autocam]"
.\.venv\Scripts\python.exe -m modules.m4_autocam source.json time_map_smartedit.json camera_plan.json
```

Voir [le contrat et les limites M4](modules/m4_autocam/README.md).

## Transcription M1

```powershell
.\.venv\Scripts\python.exe -m pip install -e ".[transcription]"
.\.venv\Scripts\python.exe -m modules.m1_transcription "projects\demo\source.json" "projects\demo\transcript.json" --model small --language fr --allow-model-download
```

Téléchargement du modèle uniquement sur demande explicite ; transcription locale ensuite.
Voir la documentation M1 pour sélectionner la piste audio, utiliser le GPU ou lancer ses tests.

