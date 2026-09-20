# M5 Visual Planner — v1.0.0

M5 analyse les contrats publics `edit_plan.json`, `transcript.json` et le mapping
SmartEdit final. `camera_plan.json` est facultatif et, lorsqu'il est fourni, sa
provenance est vérifiée. M5 ne lit aucun média, ne télécharge aucun asset et ne
modifie aucune vidéo. Il produit uniquement `visual_plan.json` pour une résolution
ultérieure par M6 Asset Manager.

## Étapes

1. `planner.py` relie passages, rôles et sections SmartEdit ;
2. `concepts.py` détecte des concepts visualisables avec des signaux lexicaux
   explicites : chiffres/données, actions, lieux/objets ou mécanismes explicatifs ;
3. `time_mapping.py` retient la plus longue intersection SOURCE réellement
   conservée et calcule sa position CUT correspondante ;
4. `selection.py` arbitre les candidats par score, espacement CUT et quota de
   section ;
5. `output.py` publie exclusivement le plan validé.

Chaque passage produit une décision dans `requests`. Une vraie demande utilise
`AUTO` ou `REVIEW` et un type `ILLUSTRATION`, `PHOTO`, `BROLL` ou
`ICON_GRAPHIC`. Les passages pour lesquels un visuel n'améliore pas suffisamment
la compréhension ou le rythme reçoivent `NONE`, avec une raison explicite. Cette
représentation permet à M6 de filtrer les demandes sans inventer d'asset.

## Contrat et prudence

[visual-plan-1.0.0.json](../../core/schemas/visual-plan-1.0.0.json) conserve les
chemins et SHA-256 de toutes les entrées, l'identité du média SOURCE, la politique
complète, les coordonnées SOURCE/CUT, le concept, le type demandé, la durée, la
priorité, la confiance et la justification.

La politique par défaut impose 3,5 secondes entre deux visuels et au plus deux
visuels par section SmartEdit. Les concepts chiffrés, actions et objets explicites
peuvent être automatiques. Une illustration conceptuelle ou un CTA isolé reste en
`REVIEW`. Un passage conservé trop court, un conflit de densité ou l'absence de
concept concret produit `NONE`.

M5 choisit une seule intersection conservée lorsqu'un passage traverse une coupe.
Il ne demande donc jamais un asset sur un intervalle supprimé par M2/M3. Les
positions CUT sont calculées à partir du mapping final, sans arithmétique flottante.

## API et CLI

```python
plan = plan_visuals(
    "edit_plan.json", "transcript.json", "time_map_smartedit.json",
    "visual_plan.json", camera_plan_path="camera_plan.json",
)
```

```powershell
.\.venv\Scripts\python.exe -m modules.m5_visual_planner `
  edit_plan.json transcript.json time_map_smartedit.json visual_plan.json `
  --camera-plan camera_plan.json
```

La sortie existante n'est jamais écrasée. Le résultat est déterministe pour les
mêmes entrées et la même configuration.

## Tests et limites

```powershell
.\.venv\Scripts\python.exe -m pytest modules/m5_visual_planner/tests -q
.\.venv\Scripts\python.exe -m pytest -q
```

Les heuristiques v1 sont locales, gratuites et explicables. Elles ne comprennent
pas les synonymes complexes, l'ironie, les références implicites ni la disponibilité
future des assets. Le corpus réel devra servir à ajuster lexiques, seuils et densité.
M6 décidera plus tard si une demande peut être satisfaite ; M5 ne recherche aucun
fichier et ne garantit aucune licence d'asset.
