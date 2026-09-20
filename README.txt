CORRECTIF M2 — token de ponctuation
===================================

Le bug:
M1 peut produire un mot horodaté qui contient uniquement de la ponctuation.
Le contrat M1 l'autorise, mais M2 refusait tout token sans caractère lexical.

Le correctif:
M2 ignore uniquement ces tokens de ponctuation pour ses heuristiques lexicales.
Les contrôles de chronologie et d'identifiants restent actifs.

Installation:
1. Extraire les fichiers à la racine de AutoReel:
   C:\Users\yoana\Documents\ChatGPT\AutoReel
2. Double-cliquer sur APPLIQUER_FIX_M2.bat
3. Retourner dans AutoReel GUI.
4. Cliquer sur « Continuer le montage ».

Le script crée automatiquement:
modules\m2_speechcut\analyze.py.before_punctuation_fix
avant modification.
