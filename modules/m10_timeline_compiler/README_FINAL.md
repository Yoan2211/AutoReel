# M10 Timeline Compiler — Final 1.0.0

M10 Final compile `timeline_draft.json` Pass A et `captions.json` M9 vers
`timeline.json`. Il ne planifie, ne segmente et ne recalcule aucune décision.

V1, V2, A1, A2 et A3 sont copiées intégralement depuis Pass A. Les éléments
`unmaterialized` et `diagnostics` sont également conservés sans changement. V3,
réservée et vide en Pass A, reçoit un événement `CAPTION` par décision M9 avec
le texte, les lignes, les trois domaines temporels, les intervalles SOURCE, les
mots horodatés, le style et la provenance M9.

Le compilateur exige que `captions.json` référence exactement le draft fourni,
par chemin résolu et SHA-256. Il vérifie la durée, les overlaps, l'égalité
CUT/TIMELINE, la projection SOURCE depuis V1 et les timings de chaque mot. Il
revérifie l'existence, la signature et le SHA-256 des deux entrées juste avant
de publier exclusivement la sortie.

Le contrat final est `core/schemas/timeline-1.0.0.json`, avec
`stage: timeline_compiler_final` et six pistes V1/V2/V3/A1/A2/A3.

```powershell
.\.venv\Scripts\python.exe -m modules.m10_timeline_compiler.final_cli `
  timeline_draft.json captions.json timeline.json
```

M10 Final ne modifie pas ses entrées, ne rend aucun média et ne contient aucune
intégration DaVinci Resolve.
