AUTOREEL DYNAMIC V3
===================

Pourquoi cette mise à jour
--------------------------
Le premier montage fonctionnait techniquement, mais il était trop conservateur :
- répétitions et retakes conservés ;
- pauses encore trop longues ;
- V2/A2/A3 souvent vides ;
- AutoCam trop dépendant des keyframes Resolve ;
- aucun vrai rythme de punch-in ;
- sous-titres parfois coupés au milieu d'un mot composé.

Dynamic V3 améliore maintenant :
- SpeechCut plus serré mais naturel ;
- suppression automatique des reprises exactes ;
- suppression automatique des retakes très similaires et proches ;
- meilleure détection des concepts médicaux ;
- génération locale de SFX discrets ;
- génération locale d'un bed musical original et très bas ;
- correction de la segmentation de sous-titres ;
- conversion HEVC 10-bit -> DNxHR HQX intégrée à M11 si nécessaire ;
- découpage V1/A1 synchronisé en plans d'environ 2.2 à 3.0 secondes ;
- alternance de punch-ins : 1.00 / 1.08 / 1.13 / 1.04 / 1.10 / 1.02 ;
- pas de dépendance obligatoire à AddKeyframe pour le rythme visuel.

Installation
------------
1. Fermer AutoReel.
2. Extraire TOUT le ZIP dans :
   C:\Users\yoana\Documents\ChatGPT\AutoReel
3. Double-cliquer sur :
   AutoReel_UPGRADE_DYNAMIC_V3.bat
4. Une fois terminé, double-cliquer sur :
   AutoReel_REBUILD_DYNAMIC_V3.bat
5. Pour le projet anemie, appuyer simplement sur Entrée.
6. La GUI se relance et reprend automatiquement à M2.

Sécurité
--------
Le rebuild ne supprime pas l'ancien montage :
il déplace les anciens artefacts dans un dossier de sauvegarde du projet.

source.json et transcript.json sont conservés.
