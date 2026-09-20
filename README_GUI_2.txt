AUTOREEL GUI 2.0
================

Objectif
--------
Une interface unique, simple et visuelle :
- 1 bouton principal qui s'adapte à l'état du projet
- reprise automatique d'un projet déjà commencé
- pipeline M0 -> M10 Final automatique
- préparation M11 pour DaVinci Resolve
- paramètres et logs masqués par défaut
- suivi visuel par grandes étapes
- suivi du téléchargement Whisper quand le modèle doit être téléchargé

Installation
------------
Fermer AutoReel GUI.

Copier / remplacer ces fichiers à la racine :
C:\Users\yoana\Documents\ChatGPT\AutoReel

- autoreel_gui.py
- AutoReel_GUI.bat

Puis double-cliquer sur AutoReel_GUI.bat.

Projet actuel
-------------
Si projects\anemie existe, l'interface le sélectionne automatiquement.
Si source.json et transcript.json existent déjà, M0 et M1 sont affichés comme
terminés et "Continuer le montage" démarre directement à M2.

Logique de l'interface
----------------------
Source
  M0

Voix
  M1 + M2 + M3

Cadrage
  M4

Habillage
  M5 + M7 + M8 + M6

Montage
  M10 Pass A + M9 + M10 Final

DaVinci
  M11 Prepare

Le dossier racine "assets" est utilisé automatiquement comme bibliothèque locale
pour images, B-roll, SFX et musique.

Important
---------
M11 Prepare ne modifie pas le projet Resolve. Une fois M11 préparé, le bouton
principal copie la commande Lua à lancer dans :
DaVinci Resolve > Workspace > Console > Lua
