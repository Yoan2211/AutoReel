AutoReel M11 VIDEO FIX

But
---
Le M11 actuel réutilise le MP4 original dans Resolve.
Si Resolve Free sous Windows ne décode que l'audio de cette source,
A1 est créée mais V1 échoue.

Ce correctif:
1. trouve automatiquement le autoreel_m11_build.lua du projet;
2. trouve le fichier source réellement référencé par M11;
3. crée un média de travail DNxHR HQX 10 bits + PCM 48 kHz;
4. conserve autant que possible les métadonnées colorimétriques;
5. laisse l'original intact;
6. crée autoreel_m11_build_VIDEO_FIX.lua qui pointe vers le média compatible;
7. affiche la commande dofile à lancer dans Resolve.

Installation
------------
Copier ces fichiers à la racine AutoReel puis lancer:
AutoReel_M11_VIDEO_FIX.bat
