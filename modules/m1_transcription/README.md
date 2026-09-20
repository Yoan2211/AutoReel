# M1 Transcription — v1.0.0

## Responsabilité et frontières

M1 transforme le JSON M0 et le média original en transcription SOURCE versionnée.
Il n'importe aucune implémentation M0 et n'effectue aucune coupe, traduction,
réécriture, déduplication, suppression d'hésitation ou création de sous-titres.
Les WAV d'analyse sont temporaires et supprimés après succès comme après erreur.
Le média original reste l'unique référence.

Les timestamps par mot sont des **estimations ASR**, pas un alignement phonétique
garanti. Whisper peut omettre des hésitations ou halluciner du texte ; M1 conserve
les estimations du moteur sans nettoyage supplémentaire. Les décisions de montage
devront être vérifiées contre l'audio dans les modules concernés.

## Entrées

API : `transcribe(manifest_path, output_path, config=None, *, backend=None) -> dict`.

- JSON conforme au contrat M0 `source-manifest-1.0.0.json`, inchangé.
- Média local original au chemin absolu du manifest. Taille et SHA-256 revérifiés
  avant décodage ; taille/date/identité revérifiées avant publication.
- Une piste audio : sélection automatique si unique. Plusieurs pistes : index
  explicite requis (`--audio-stream-index`, index global FFmpeg, pas rang audio).
- Pas d'audio : erreur explicite, aucun transcript artificiel.
- Destination JSON nouvelle ; refuser toute cible existante, même la source
  ou le manifest. Aucun résultat partiel en cas d'erreur de transcription.
- Un moteur injectable via le Protocol de `backend.py` pour les tests M1 seulement ;
  les autres modules consomment le JSON, jamais ces objets Python.

## Sortie stable

Schéma : [transcript-1.0.0.json](../../core/schemas/transcript-1.0.0.json).

- `schema_version = 1.0.0`, `module = {id: M1, version: 1.0.0}`.
- `time_domain = SOURCE` ; aucun temps CUT ou TIMELINE.
- `source` : chemin et SHA-256 originaux, empreinte des octets du manifest M0 lu,
  index de la piste transcrite. Pas de chemin WAV temporaire dans le JSON.
- `analysis` : origine SOURCE audio, durée réellement décodée, mono 16 kHz.
- `engine` : nom/version du moteur, modèle demandé, dispositif et précision effectifs.
- `options` : langue demandée, beam size et politique de transcription.
- `language`, `language_probability` : langue retournée par le moteur et score.
- `segments[]` : identifiants positionnels déterministes, texte conservé,
  `start_us`/`end_us`, score de non-parole et `words[]`.
- `words[]` : identifiant unique, texte (espaces/ponctuation conservés),
  `start_us`/`end_us`, probabilité du moteur.
- `text` concatène les textes des segments et retire uniquement les espaces externes.
- `status` : `transcribed` ou `no_speech_recognized` avec listes vides.
  Ce dernier signifie que le moteur n'a rien reconnu, pas une preuve de silence.
- Scores entre 0 et 1 : indices du modèle, pas des garanties d'exactitude.
- Avertissements : `CPU_FALLBACK`, `NO_SPEECH_RECOGNIZED`,
  `ZERO_DURATION_WORD_ESTIMATE`, `OVERLAPPING_WORD_ESTIMATES`.

Schéma structurel vérifié avant publication. La normalisation contrôle aussi
ordre chronologique, bornes, présence des mots et scores finis. Elle refuse
les timestamps inversés ou hors audio ; aucun clamp ni déplacement silencieux.
Les mots de durée nulle et les chevauchements sont conservés avec avertissement,
sans les transformer en décisions de coupe.

## Temps et décodage

L'origine vient de `source.audio[n].start_us` de M0 ; elle peut être négative
ou différente du début vidéo. FFmpeg conserve les PTS avec `-copyts`, soustrait
cette origine et utilise `aresample` pour préserver les trous temporels par silence.
Le WAV temporaire est mono PCM 16 bits à 16 kHz. Ce dérivé sert uniquement à l'ASR.

Toutes les conversions d'unités et le décalage d'origine passent par `core/time.py` :
`us_to_seconds_text`, `seconds_to_timestamp_us` et `ticks_to_us`.
L'adaptateur convertit les floats natifs du moteur en texte décimal avant ces appels.
Les intervalles sont semi-ouverts [start_us, end_us), avec tolérance explicite
pour les estimations de mots de durée nulle signalées.

La transcription couvre la piste audio, y compris ses débords éventuels sur la
vidéo et le padding de codec. Elle n'est pas coupée selon la durée vidéo de M0,
qui peut elle-même être estimée. Les fichiers aux PTS pathologiques restent un
cas à examiner sur corpus réel. Les tests incluent offset, priming AAC et trou
de timestamps effectivement présent dans un MOV/AAC.

## Configuration et installation

```powershell
.\.venv\Scripts\python.exe -m pip install -e ".[test,transcription]"
.\.venv\Scripts\python.exe -m modules.m1_transcription "projects\demo\source.json" "projects\demo\transcript.json" --model small --language fr --allow-model-download
```

Le premier téléchargement explicite alimente `models/faster-whisper/`.
Les exécutions suivantes peuvent omettre `--allow-model-download` et restent hors ligne.
Aucun média n'est envoyé au réseau. Un chemin de modèle local complet peut remplacer
`small` ; `model.bin`, `config.json` et `tokenizer.json` sont vérifiés avant chargement
pour éviter un téléchargement implicite de tokenizer.

| Option | Défaut |
| --- | --- |
| model | small (ou chemin local) |
| models_dir | models/faster-whisper |
| language | détection automatique ; fr pour forcer le français |
| audio_stream_index | automatique uniquement si une seule piste |
| device | cpu ; autres valeurs cuda, auto |
| cpu_fallback | true ; désactiver avec --no-cpu-fallback |
| allow_model_download | false |
| beam_size | 5 |
| cpu_threads | 4 |
| ffmpeg | ffmpeg dans PATH |
| decode_timeout_s | 600 |

CPU : int8. CUDA : float16, bibliothèques NVIDIA compatibles requises.
Un échec CUDA au chargement ou durant l'itération ASR déclenche une nouvelle
transcription CPU, signalée dans le résultat, si le fallback est autorisé.
Le CPU est le défaut pour éviter de dépendre d'une installation CUDA.
L'inférence ASR n'a pas de délai maximal interne ; le timeout concerne FFmpeg.

VAD désactivé, tâche transcribe, température 0 et contexte du segment précédent
désactivé. Le moteur peut néanmoins décider qu'un passage ne contient pas de parole.
Un contrôle strict détecte une piste PCM entièrement à zéro avant tout chargement
ASR et produit un résultat vide avec moteur `pcm-silence-check` (version 1.0.0).
Aucun seuil de volume n'est appliqué ; un seul échantillon non nul laisse passer
l'audio vers l'ASR. Dans ce cas vide, la langue vaut la langue demandée ou `und`,
et son score vaut 0. Ce contrôle n'analyse ni bruit ambiant ni pauses locales.

M1 v1 ne propose ni diarisation ni forced alignment.

## Erreurs, écriture et fichiers

`TranscriptionError` pour contrat/média/ASR invalides ; `OSError` pour les erreurs
filesystem, notamment `FileExistsError`. La CLI renvoie 1 avec diagnostic stderr,
0 après publication. Une annulation Python nettoie le WAV temporaire.

M1 écrit exclusivement un nouveau fichier JSON et retire une écriture interrompue
par une exception interceptée. Il ne dépend pas des hard links de M0. Cette écriture
n'est pas atomique face à un arrêt brutal du processus ou une panne machine :
dans ce cas supprimer/revoir explicitement le fichier incomplet avant de relancer.
Un consommateur attend le succès de M1 et valide le JSON avant lecture.

## Tests reproductibles

Tests isolés M1 sans télécharger de modèle :

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s modules/m1_transcription/tests -t . -v
```

Le test ASR Windows utilise la synthèse vocale locale System.Speech et un modèle
déjà présent, sans réseau. Pour l'activer puis vérifier aussi les non-régressions :

```powershell
$env:AUTOREEL_TEST_MODEL = "CHEMIN_ABSOLU_DU_MODELE_LOCAL"
.\.venv\Scripts\python.exe -m unittest discover -v
```

Sans ce paramètre, les tests ASR réels sont explicitement ignorés. Les tests médias
nécessitent FFmpeg/FFprobe. Les tests de fallback GPU utilisent des erreurs simulées :
ils ne constituent pas une validation sur carte NVIDIA réelle.

## Références techniques

- [faster-whisper : mots horodatés, CPU et GPU](https://github.com/SYSTRAN/faster-whisper)
- [FFmpeg : filtres audio et PTS](https://ffmpeg.org/ffmpeg-filters.html)
- Options vérifiées aussi avec `ffmpeg -h filter=aresample` et le code
  faster-whisper 1.2.1 installé dans l'environnement de validation.
