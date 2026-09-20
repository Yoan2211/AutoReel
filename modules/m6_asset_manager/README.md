# M6 Asset Manager — v1.0.0

M6 transforme les demandes abstraites de M5, M7 et M8 en références concrètes
dans `assets_manifest.json`. Il cherche exclusivement dans une bibliothèque locale.
Il ne télécharge, ne génère, ne monte et ne modifie aucun média source.

## Étapes isolées

1. `requests.py` collecte uniquement les demandes actives des trois plans ;
2. `library.py` indexe récursivement les formats locaux pris en charge ;
3. `scoring.py` compare type, intention, concept, nom, dossiers et tags ;
4. `resolution.py` choisit le meilleur candidat déterministe et déduplique ;
5. `probe.py` et `validation.py` vérifient format, flux, métadonnées, taille et
   SHA-256 sans altérer le fichier ;
6. `manager.py` valide et publie exclusivement `assets_manifest.json`.

## Bibliothèque locale

Extensions v1 :

- images/illustrations/graphics : PNG, JPEG et WebP ;
- B-roll : MP4, MOV, MKV et WebM ;
- SFX/musique : WAV, MP3, FLAC, M4A, AAC et OGG.

Le type est inféré du format et des dossiers `photos`, `illustrations`, `graphics`,
`broll`, `sfx` et `music`. Un sidecar facultatif placé à côté du média permet
d'ajouter des tags ou de préciser le type :

```json
{
  "asset_type": "SFX",
  "tags": ["whoosh", "soft", "transition"]
}
```

Pour `whoosh_soft.wav`, le sidecar se nomme `whoosh_soft.wav.asset.json`. Un
sidecar invalide exclut le candidat et reste visible dans `library_issues`.

## Résolution et stabilité

Le score privilégie d'abord la compatibilité stricte du type, puis le type demandé,
le concept/mood, le nom, les dossiers et les tags. À partir de 0,72, une demande
forte peut devenir `RESOLVED`. Entre 0,50 et 0,72, ou si la demande amont était
`REVIEW`, la correspondance reste `REVIEW`. Sans candidat validé, elle devient
`UNRESOLVED` avec `asset_id: null` ; aucun chemin n'est inventé.

L'identifiant est dérivé du type et des seize premiers caractères du SHA-256,
par exemple `sfx_a1b2c3d4e5f60718`. Le même contenu physique réutilisé garde donc
le même identifiant. Une seule entrée `assets` liste tous ses `request_ids`.

Les chemins situés sous la racine projet sont stockés avec `/` et marqués
`PROJECT_RELATIVE`. Un asset externe conserve un chemin absolu accompagné de
l'avertissement `ABSOLUTE_ASSET_PATHS`.

## Métadonnées validées

FFprobe confirme que le fichier contient le flux attendu. Le manifest conserve :

- audio : format, codec, durée, fréquence d'échantillonnage, canaux et loudness
  si disponible (`null` dans le backend FFprobe v1 lorsqu'elle n'est pas mesurée) ;
- image : format, codec et dimensions ;
- vidéo : format, codec, dimensions et durée.

La taille et le SHA-256 sont calculés après le sondage. M6 refuse un fichier qui
change pendant cette validation.

## API et CLI

```python
manifest = resolve_assets(
    "visual_plan.json", "sound_plan.json", "music_plan.json",
    "assets", "assets_manifest.json",
)
```

```powershell
.\.venv\Scripts\python.exe -m modules.m6_asset_manager `
  visual_plan.json sound_plan.json music_plan.json assets assets_manifest.json
```

Le résultat est déterministe pour les mêmes plans, fichiers, sidecars et seuils.
Une sortie existante n'est jamais écrasée.

## Tests et limites

```powershell
.\.venv\Scripts\python.exe -m pytest modules/m6_asset_manager/tests -q
.\.venv\Scripts\python.exe -m pytest -q
```

Les tests couvrent bibliothèque vide, six familles d'assets, scoring, sidecars,
réutilisation, IDs stables, chemins portables, fichiers invalides, provenance,
non-écrasement et sondages FFprobe réels WAV/PNG/MP4.

M6 v1 n'utilise ni catalogue distant ni modèle de similarité sémantique. La qualité
du matching dépend de noms et tags descriptifs. La loudness intégrée n'est pas
mesurée automatiquement ; elle reste `null` plutôt que d'être inventée.
