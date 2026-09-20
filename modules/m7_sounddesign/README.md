# M7 SoundDesign — v1.0.0

M7 est un planner de bruitages. Il analyse `transcript.json`, `edit_plan.json`,
`visual_plan.json`, `camera_plan.json` et le mapping SmartEdit final, puis produit
`sound_plan.json`. Il ne recherche, ne télécharge, ne génère, ne mixe et n'insère
aucun fichier audio. M6 Asset Manager résoudra plus tard les demandes retenues.

## Étapes isolées

1. `collection.py` collecte hooks, phrases fortes, apparitions visuelles,
   changements de section, zooms et discontinuités SOURCE ;
2. `classification.py` associe un type de SFX et un gain recommandé ;
3. `prioritization.py` score les événements et choisit un gagnant par conflit ;
4. le même composant applique espacement et densité globale ;
5. `planner.py` génère toutes les décisions, y compris les `NONE`, puis
   `output.py` publie exclusivement `sound_plan.json`.

La conversion SOURCE→CUT utilise [core/timeline.py](../../core/timeline.py), en
microsecondes entières. Un événement tombant dans une plage supprimée par M2/M3
est ignoré.

## Arbitrage et voix prioritaire

Par défaut, deux SFX actifs doivent être espacés d'au moins 3 secondes et le plan
ne peut pas dépasser huit SFX dans une fenêtre de 60 secondes. Les événements à
moins de 300 ms sont regroupés. Une apparition visuelle prime alors sur le hook,
la phrase forte, la transition, le changement de section et le zoom. Un seul son
survit ; les autres décisions restent présentes avec `type: NONE`, `status: NONE`
et une justification.

Un score supérieur ou égal à 0,78 produit `PROPOSED`. Entre 0,62 et 0,78, la
décision reste `REVIEW`. En dessous, M7 choisit `NONE`. Les gains conseillés sont
volontairement discrets, de −27 dB à −23 dB selon le type. Ils sont des métadonnées
pour une étape de mixage ultérieure ; M7 ne touche jamais au signal vocal.

Types du contrat : `SOFT_IMPACT`, `POP`, `CLICK`, `WHOOSH`, `SWOOSH`, `RISER`,
`ACCENT` et `NONE`. Le backend v1 choisit notamment un impact doux pour le hook,
un pop/clic pour certains éléments graphiques, un whoosh pour une apparition ou
transition et un swoosh doux pour un zoom ponctuel.

## Contrat et provenance

[sound-plan-1.0.0.json](../../core/schemas/sound-plan-1.0.0.json) conserve les
chemins et SHA-256 exacts des cinq entrées, l'identité du média SOURCE, la politique
complète et chaque décision avec `source_time_us`, `cut_time_us`, type, statut,
gain, priorité, confiance, score, origine et raison.

M7 refuse toute rupture de provenance entre M1, M3, M4 et M5. Si M5 a été généré
avec un plan caméra, son empreinte doit correspondre au plan caméra fourni à M7.
Une sortie existante n'est jamais écrasée.

## API et CLI

```python
plan = plan_sounds(
    "transcript.json", "edit_plan.json", "visual_plan.json",
    "camera_plan.json", "time_map_smartedit.json", "sound_plan.json",
)
```

```powershell
.\.venv\Scripts\python.exe -m modules.m7_sounddesign `
  transcript.json edit_plan.json visual_plan.json camera_plan.json `
  time_map_smartedit.json sound_plan.json
```

## Tests et limites

```powershell
.\.venv\Scripts\python.exe -m pytest modules/m7_sounddesign/tests -q
.\.venv\Scripts\python.exe -m pytest -q
```

Les tests couvrent classification, hooks, visuels, sections, transitions, zooms,
conflits simultanés, espacement, limite glissante, `NONE`, gains, SOURCE→CUT,
passages supprimés, déterminisme, provenance et non-écrasement.

Les heuristiques v1 devront être évaluées à l'écoute sur des montages français
réels. Le plan ne connaît ni timbre, ni durée exacte, ni licence du futur fichier
sonore. Ces propriétés appartiendront à M6 et aux étapes de compilation/mixage.
