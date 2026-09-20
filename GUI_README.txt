AUTOREEL GUI v1.0
=================

Installation
------------
Copier ces trois fichiers à la RACINE de :

C:\Users\yoana\Documents\ChatGPT\AutoReel

Fichiers :
- autoreel_gui.py
- AutoReel_GUI.bat
- GUI_README.txt

Lancement
---------
Double-cliquer sur :

AutoReel_GUI.bat

Aucun PowerShell n'est nécessaire pour l'utilisation normale.

Ce que v1 pilote directement
-----------------------------
- sélection de la vidéo
- création/reprise du dossier projects\<nom_projet>
- M0 Ingest
- M1 Transcription
- détection visuelle des artefacts M0 → M10
- préparation M11 dès que timeline.json existe
- journal d'exécution
- arrêt d'une commande en cours
- ouverture du dossier projet

Projet anemie
-------------
Le projet déjà commencé est détecté dans :

projects\anemie

Si source.json existe déjà, M0 est marqué OK et peut être conservé.
Il suffit ensuite de choisir la vidéo source, garder "anemie" comme nom de projet,
puis cliquer sur "M0 → M1 automatique" : M0 est ignoré s'il existe et M1 démarre.

Important
---------
Cette GUI v1 n'invente pas les appels M2→M10 qui n'ont pas encore été branchés
à l'interface. Elle affiche néanmoins leur état dès que leurs artefacts existent.
L'architecture est prête pour ajouter progressivement les boutons M2→M10 sans
modifier les modules validés.
