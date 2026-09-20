# M10 Timeline Compiler — Pass A 1.0.0

M10 Pass A compile les décisions validées des modules amont en
`timeline_draft.json`. Il ne prend aucune décision éditoriale et ne crée aucun
média. Il publie exclusivement un nouveau fichier.

## Entrées et sortie

Entrées : manifest M0 (`media_info.json`), mapping M3 définitif,
`edit_plan.json`, `camera_plan.json`, `visual_plan.json`, `sound_plan.json`,
`music_plan.json` et `assets_manifest.json`. Les schémas, empreintes de
provenance et l'identité du média SOURCE sont validés avant compilation.

La sortie respecte `core/schemas/timeline-draft-1.0.0.json` et contient :

- V1 : clips vidéo SOURCE reconstruits depuis chaque segment conservé par M3 ;
- V2 : visuels et B-roll dont la requête M6 est `RESOLVED` ;
- V3 : piste vide réservée aux futurs graphics/captions ;
- A1 : voix SOURCE reconstruite avec les mêmes segments que V1 ;
- A2 : musique résolue, fades et régions de niveau/ducking de M8 ;
- A3 : SFX résolus, à leur ancre M7 et avec leur durée de fichier M6.

SOURCE, CUT et TIMELINE ont des champs séparés. Pass A place CUT à la même
position numérique que TIMELINE, mais le contrat ne les confond jamais. Les
keyframes M4 sont projetées et attachées aux événements V1.

Pass A accepte zéro piste audio SOURCE ou une seule. Plusieurs pistes audio sans
contrat amont désignant explicitement la voix sont refusées comme ambiguës.

Les demandes M6 `REVIEW` et `UNRESOLVED` restent dans `unmaterialized`. Aucun
chemin n'est inventé. La compilation échoue sur provenance ou mapping
impossible, intervalle supprimé, durée non positive, fichier résolu absent ou
modifié, type d'asset incorrect, overlap de piste, piste invalide ou timestamp
incohérent.

## CLI

```powershell
.\.venv\Scripts\python.exe -m modules.m10_timeline_compiler `
  media_info.json time_map_smartedit.json edit_plan.json camera_plan.json `
  visual_plan.json sound_plan.json music_plan.json assets_manifest.json `
  timeline_draft.json
```

Cette version est uniquement Pass A. Elle ne contient ni captions M9, ni Pass
Final, ni intégration Resolve M11.
