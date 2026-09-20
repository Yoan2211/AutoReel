# AutoReel — règles de développement

## Architecture obligatoire
- Ne jamais construire un script monolithique. Chaque module a une responsabilité,
  des entrées/sorties documentées, des tests, une version et sa configuration si utile.
- Échanger uniquement par contrats stables : JSON, médias, manifests et timestamps.
  Aucun accès aux variables ou à l'implémentation interne d'un autre module.
- Structure : `core/` (contrats, temps, configuration, logs, timeline), `modules/`
  (un dossier par module), `models/`, `assets/`, `projects/`, `tests/`, `tools/`.
- Pipeline : M0 Ingest → M1 Transcription → M2 SpeechCut → M3 SmartEdit →
  M4 AutoCam → M5 Visual Planner → M7 SoundDesign → M8 Music → M6 Asset Manager →
  M10 Timeline Compiler pass A → M9 Captions → M10 Timeline Compiler final →
  M11 Resolve Builder → M12 Quality Control.
- AutoCam analyse la vidéo SOURCE originale, uniquement sur les intervalles conservés
  après SpeechCut et SmartEdit. Aucun réencodage intermédiaire ne devient référence.
- Distinguer explicitement SOURCE, CUT et TIMELINE. Temps canoniques : entiers
  microsecondes, suffixe `_us`. Centraliser toutes les conversions dans `core/time.py`.
- Visual Planner, SoundDesign et Music demandent des assets ; Asset Manager les résout.
- Captions intervient après la compilation pass A.
- Resolve Builder crée toujours une nouvelle timeline ; aucun écrasement.

## Méthode et validation
- SEGMENTER → CODER → TESTER → CORRIGER → RETESTER → VALIDER → MODULE SUIVANT.
- Un seul module à la fois, jamais plusieurs modules en parallèle.
- Avant chaque module, inspecter architecture, contrats et état de validation.
- Définir précisément les entrées/sorties, implémenter, ajouter les tests, les exécuter,
  corriger et retester jusqu'à stabilité. Rapporter changements, résultats et limites.
- S'arrêter AVANT le module suivant pour validation explicite de l'utilisateur.
  Des tests réussis ne constituent pas cette validation. Voir `docs/STATUS.md`.
- Si un test échoue, corriger le module concerné d'abord. Modifier un autre module
  uniquement si la nécessité est démontrée et expliquée.
- Ne jamais changer silencieusement un contrat existant : expliquer le problème et
  proposer la modification AVANT de la réaliser.
- Préserver les médias sources et le travail utilisateur ; refuser les écrasements.

## Cible et critères produit
- Windows 10, Python 3.11, FFmpeg/FFprobe, DaVinci Resolve 21.0.4 Free.
- Entrées smartphone MP4/MOV, H.264/H.265/HEVC, HDR/HLG possibles.
- Sortie habituelle 1080×1920, 9:16 ; gratuit/open source en priorité.
- GPU NVIDIA facultatif ; fallback CPU lorsque raisonnable.
- Voix claire prioritaire, montage naturel et dynamique, suppression intelligente
  des hésitations/répétitions, respirations naturelles, zooms subtils, cadrage auto,
  B-roll pertinent, SFX contextuels subtils, musique avec ducking, sous-titres,
  timeline éditable dans Resolve.
