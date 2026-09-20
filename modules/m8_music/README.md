# M8 Music Planner — v1.0.0

M8 planifie une ambiance musicale sans rechercher, télécharger, générer, mixer ou
insérer de fichier audio. Il lit `transcript.json`, `edit_plan.json`, le mapping
SmartEdit final, `visual_plan.json` et `sound_plan.json`, puis publie
`music_plan.json`. M6 Asset Manager résoudra ultérieurement la demande vers un
morceau réel.

## Étapes isolées

1. `context.py` analyse les thèmes SmartEdit et l'intensité visuelle ;
2. `decision.py` choisit `MUSIC`, `REVIEW` ou `NONE` selon la durée et la clarté
   de l'intention ;
3. le contexte fournit un mood et une énergie explicables ;
4. `planner.py` crée une région musicale CUT continue ;
5. `levels.py` calcule ducking vocal, pauses, fades et niveaux ;
6. les SFX actifs créent des zones protégées qui interdisent une remontée ;
7. `output.py` publie exclusivement le plan validé.

Les conversions d'intervalles SOURCE/CUT sont centralisées dans
[core/time_ranges.py](../../core/time_ranges.py). Une région CUT traversant des
coupes conserve chaque intervalle SOURCE correspondant dans `source_intervals`.

## Voix prioritaire et stabilité

Le niveau par défaut sous parole est −28 dB, configurable uniquement dans la plage
−30 à −25 dB. Une pause sans parole d'au moins 1,5 seconde peut remonter à −21 dB.
Les pauses de moins de 300 ms sont fusionnées avec la parole ; les autres pauses
trop courtes restent à `STABLE_BASE`. La musique ne pompe donc pas entre les mots.

Chaque SFX `PROPOSED` ou `REVIEW` protège 600 ms avant et après son timestamp.
Dans cette zone, M8 conserve le niveau sous parole au lieu de remonter la musique.
La voix l'emporte toujours si parole et SFX se chevauchent.

M8 produit par défaut un seul lit `STABLE_BED` sur le programme CUT. Les changements
de section, visuels et SFX n'entraînent pas de nouvelle région musicale. Les fades
d'entrée/sortie sont plafonnés à la moitié de la durée pour les formats courts.

## Décision et demande d'asset

- moins de 8 secondes ou aucune parole reconnue : `NONE` ;
- entre 8 et 15 secondes, ou thème musical ambigu : `REVIEW` ;
- programme plus long avec thème identifiable : `MUSIC`.

Les moods v1 sont locaux et déterministes : médical, technologie, business,
éducation, récit chaleureux ou neutre moderne. La demande contient mood, énergie,
durée et acceptation d'une boucle propre. Elle ne contient ni titre, ni artiste,
ni chemin de fichier, ni fournisseur.

## Contrat et exécution

[music-plan-1.0.0.json](../../core/schemas/music-plan-1.0.0.json) conserve les
empreintes des cinq entrées, l'identité du média, la politique, la décision, la
demande M6, la région musicale et toutes les régions de niveau SOURCE/CUT.

```powershell
.\.venv\Scripts\python.exe -m modules.m8_music `
  transcript.json edit_plan.json time_map_smartedit.json `
  visual_plan.json sound_plan.json music_plan.json
```

La sortie existante n'est jamais écrasée. Le résultat est déterministe pour les
mêmes entrées et la même configuration.

## Tests et limites

```powershell
.\.venv\Scripts\python.exe -m pytest modules/m8_music/tests -q
.\.venv\Scripts\python.exe -m pytest -q
```

Les tests couvrent MUSIC/REVIEW/NONE, moods, stabilité, fades, ducking, remontées,
pauses courtes, conflits SFX, mappings discontinus, provenance, déterminisme et
non-écrasement.

Les niveaux sont des recommandations, pas un mixage loudness mesuré. Les moods et
seuils devront être évalués à l'écoute sur des contenus français réels. M6 choisira
le fichier, vérifiera sa licence et sa capacité de boucle ; M8 ne garantit aucun
asset concret.
