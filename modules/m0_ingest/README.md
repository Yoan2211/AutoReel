# M0 Ingest — v1.0.0

## Responsabilité

Inspecter un MP4/MOV original et publier un manifest SOURCE sans modifier,
copier ou réencoder le média. FFprobe travaille sur le fichier original.
Le SHA-256 est calculé en lecture par blocs ; le fichier doit être au repos.
La taille, la date de modification et l'identité du fichier sont contrôlées
avant/après l'ingest afin de détecter les changements usuels pendant la lecture.

## Entrées et configuration

API publique : `ingest(source, manifest_path, IngestConfig(...)) -> dict`.
CLI : `python -m modules.m0_ingest SOURCE MANIFEST [--ffprobe PATH] [--timeout-s 60]`.

- Source locale existante, non vide, extension MP4/MOV et conteneur FFprobe MP4/MOV.
- Destination JSON neuve ; création des parents autorisée, tout écrasement refusé.
- `ffprobe` : nom ou chemin de l'exécutable ; `timeout_s` : entier positif, défaut 60.
- Sélection vidéo : ignorer les couvertures, préférer le stream par défaut,
  puis le plus petit index. Toutes les pistes audio sont décrites.
- H.264/HEVC et autres codecs du conteneur sont décrits sans prétendre garantir
  leur décodage dans Resolve Free. Aucun GPU requis.

## Sortie et contrat stable

Schéma : [source-manifest-1.0.0.json](../../core/schemas/source-manifest-1.0.0.json).
`schema_version` et `module.version` sont indépendants et fixés à `1.0.0`.

- `source.path` : chemin absolu du média original ; `sha256` : identité de contenu.
  Déplacer le projet nécessite une relocalisation explicite future, pas une substitution.
- `time_domain = SOURCE` : temps de présentation du média original.
  `start_us` est le PTS de départ du stream vidéo, éventuellement négatif ou non nul.
  Intervalle vidéo semi-ouvert : [start_us, start_us + duration_us).
  Les pistes audio gardent leurs propres débuts ; ne pas les forcer à zéro.
- `duration_us` privilégie duration_ts × time_base puis la durée du stream.
  Faute de durée vidéo, la durée conteneur est une estimation signalée,
  pas une borne exacte pour les futurs découpages.
- Toutes les conversions passent par `core/time.py` : calcul rationnel/décimal,
  arrondi au microseconde le plus proche, égalité éloignée de zéro.
  Aucune conversion SOURCE↔CUT↔TIMELINE n'est encore nécessaire ou implémentée.
- Dimensions encodées, dimensions après rotation orthogonale et rotation modulo 360.
  La rotation conserve le signe de la valeur FFprobe modulo 360 ; un futur adaptateur
  Resolve devra convertir explicitement sa convention. Le ratio de pixels est séparé :
  display_width/height ne corrige pas l'anamorphose.
- Fréquences d'images rationnelles ; `frame_timing = UNDETERMINED` :
  aucune supposition CFR, aucune conversion timestamp par index de frame.
- Métadonnées couleur et classification HLG/PQ/SDR/UNKNOWN selon le transfert déclaré.
  Aucune conversion HDR→SDR ni inspection complète des métadonnées Dolby Vision.
- Avertissements structurés : audio absent, transfert inconnu, HDR, durée estimée,
  plusieurs vidéos avec sélection d'une piste primaire.

## Erreurs et limites

L'API lève `IngestError` pour média/métadonnées/FFprobe invalides,
ou une exception `OSError` (dont `FileExistsError`) pour les erreurs filesystem.
La CLI renvoie 1 avec diagnostic sur stderr, 0 après succès.
Une source sans audio est acceptée avec avertissement ; M1 décidera de sa politique.
Les rotations non orthogonales sont refusées explicitement.
FFprobe inspecte les métadonnées, sans garantir l'intégrité de chaque frame.
Les cas réels smartphone HDR/HEVC et Resolve restent à valider sur l'environnement cible.

## Tests

`python -m unittest discover -v` depuis la racine.
Tests isolés par répertoires temporaires : contrat JSON, identité et protection
de la source, absence d'écrasement, choix des pistes, HDR, rotation, offsets,
durées, erreurs FFprobe, timeout, configuration ; conversions dans `tests/`.
Un test réel génère un MP4 via FFmpeg, exécute FFprobe et vérifie le manifest.


Publication : fichier temporaire voisin puis lien dur exclusif (NTFS recommandé). Un filesystem sans liens durs provoque une erreur explicite sans publier de manifest incomplet. Une destination créée concurremment reste intacte.
