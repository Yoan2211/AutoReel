AutoReel GUI 2.1

Corrections:
- Le bouton « Continuer le montage » finalise maintenant réellement M10 Final.
- Cause corrigée: final_cli.py définit main() mais n'est pas exécuté directement avec python -m.
- Ajout de AutoReel_PREPARATION.bat :
  vérifie FFmpeg/FFprobe, les dépendances Python, OpenCV et Whisper small,
  et propose de télécharger Whisper small s'il manque.

Installation:
1. Fermer AutoReel.
2. Copier/remplacer autoreel_gui.py et AutoReel_GUI.bat à la racine du projet.
3. Copier aussi autoreel_prepare.py et AutoReel_PREPARATION.bat.
4. Relancer AutoReel_GUI.bat.
5. Pour vérifier l'installation complète à tout moment, lancer AutoReel_PREPARATION.bat.
