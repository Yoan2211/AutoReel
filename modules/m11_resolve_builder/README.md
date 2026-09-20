# M11 Resolve Builder v1.0.0 — Resolve Free 21.0.4

M11 reste compatible avec DaVinci Resolve Free 21.0.4 :

1. Python AutoReel valide `timeline.json`, vérifie les SHA-256 et génère un Lua.
2. Le Lua s'exécute dans Resolve via `Workspace > Console`.

Aucun External Scripting Studio n'est requis.

## Préparation

```powershell
.\.venv\Scripts\python.exe -m modules.m11_resolve_builder.prepare `
  --timeline "CHEMIN\VERS\timeline.json" `
  --fps "60000/1001"
```

La timeline `anemia` mesurée dans Resolve est actuellement en 59.94 fps, donc
`60000/1001` est le rationnel à utiliser pour ce test.

La commande crée `m11_resolve_build`, puis `_001`, `_002`, etc. sans écraser.

## Exécution

La commande Python affiche une commande :

```lua
dofile([[C:\...\autoreel_m11_build.lua]])
```

Dans Resolve : `Workspace > Console` → Lua → colle la commande → Entrée.

## Sécurité

- nouvelle timeline uniquement : `AutoReel`, `AutoReel_001`, etc.
- aucune timeline existante supprimée/modifiée ;
- V1 = vidéo seulement ;
- A1 = audio seulement, afin d'éviter la voix doublée ;
- V2, A2, A3 sont placés selon M10 ;
- AutoCam applique le zoom M4, dynamiquement si `AddKeyframe` existe réellement ;
- le SRT M9 est importé au Media Pool.

## Limites v1 signalées dans le rapport

Resolve 21.0.4 n'expose pas de méthode supportée pour créer directement chaque
SubtitleItem à son timecode. Le SRT est donc importé, mais l'insertion finale est
marquée `CAPTION_TIMELINE_INSERTION`.

Le mapping M4 `center_x/center_y` vers Resolve `Pan/Tilt` n'est pas deviné :
`AUTOCAM_CENTER_PAN_TILT_CALIBRATION` est signalé tant que nous n'avons pas
calibré ces unités sur ton installation.

Les fades musique / automations sont appliqués seulement si la fonction de
keyframe réelle répond ; sinon ils sont signalés `UNSUPPORTED`.

## Rapport

Le Lua tente d'écrire `resolve_build_report.json` si `io.open` est disponible.
Sinon le JSON complet est imprimé dans la Console avec :

`AUTOREEL_REPORT_JSON=...`
