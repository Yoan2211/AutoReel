# État de validation AutoReel

Le dépôt initial était vide, sans commit, architecture ou contrat préexistant.
Aucune modification de contrat préexistant n'a donc été nécessaire.

| Élément | État |
| --- | --- |
| Socle partagé (temps et schémas) | M0 inchangé ; ajouts minimaux pour M1 |
| M0 Ingest 1.0.0 | Accepté par l'utilisateur le 19 septembre 2026 ; gelé sauf bug bloquant démontré |
| M1 Transcription 1.0.0 | Accepté par l'utilisateur le 19 septembre 2026 ; gelé sauf bug bloquant démontré |
| M2 SpeechCut 1.0.0 | Accepté par l'utilisateur le 19 septembre 2026 ; gelé sauf bug bloquant démontré |
| M3 SmartEdit 1.0.0 | Accepté par l'utilisateur le 20 septembre 2026 ; gelé sauf bug bloquant démontré |
| M4 AutoCam 1.0.0 | Accepté par l'utilisateur le 20 septembre 2026 ; gelé sauf bug bloquant démontré |
| M5 Visual Planner 1.0.0 | Accepté par l'utilisateur le 20 septembre 2026 ; gelé sauf bug bloquant démontré |
| M7 SoundDesign 1.0.0 | Accepté par l'utilisateur le 20 septembre 2026 ; gelé sauf bug bloquant démontré |
| M8 Music Planner 1.0.0 | Accepté par l'utilisateur le 20 septembre 2026 ; gelé sauf bug bloquant démontré |
| M6 Asset Manager 1.0.0 | Accepté par l'utilisateur le 20 septembre 2026 ; gelé sauf bug bloquant démontré |
| M10 pass A 1.0.0 | Accepté par l'utilisateur le 20 septembre 2026 après correction de l'import bloquant ; gelé |
| M9 Captions 1.0.0 | Accepté par l'utilisateur le 20 septembre 2026 après correction de la longueur des lignes ; gelé |
| M10 final 1.0.0 | Implémenté et testé ; en attente de validation utilisateur |
| M11 Resolve Builder | Non commencé |
| M12 Quality Control | Non commencé |

M0–M9 et M10 Pass A acceptés pour poursuivre. M10 Final attend sa validation explicite.



## M0 — vérification initiale du 19 septembre 2026

- Installation éditable réussie dans `.venv` sous Python 3.11.9.
- `python -m unittest discover -v` : **20 tests réussis, 0 échec, 0 ignoré**.
- Même suite réussie également sous Python 3.12.14.
- Intégration réelle : génération d'un MP4 vidéo + audio avec FFmpeg, lecture
  FFprobe, ingest et validation du manifest contre le schéma JSON.
- Tests HDR/HEVC et rotation fondés sur des métadonnées simulées ; les médias
  smartphone réels HDR/HLG/HEVC et la compatibilité Resolve restent à vérifier.
- Les outils Python 3.11/FFmpeg/FFprobe et les dépendances sont accessibles hors
  sandbox ; l'environnement restreint masquait ces exécutables. Les tests ont
  été exécutés avec les autorisations accordées.
- M0 n'effectue aucun décodage complet, tone mapping ni import Resolve.
- Publication atomique du manifest par lien dur : destination sur NTFS ou autre
  filesystem prenant en charge les liens durs requise.

Backlogs M0 et M1 : voir docs/BACKLOG.md.


## M1 — vérification du 19 septembre 2026

- M0 accepté par l'utilisateur avant ce développement ; 11 empreintes de fichiers
  M0 (code, tests, README et schéma) vérifiées identiques avant/après M1.
- Socle partagé : deux fonctions temporelles ajoutées, sans modifier les fonctions
  existantes ; nouveau schéma transcript 1.0.0. Aucun changement du contrat M0.
- Python 3.11.9 ; faster-whisper 1.2.1 ; CTranslate2 4.8.2 ; PyAV 18.1.0 ;
  jsonschema 4.26.0. Installation éditable avec extra transcription réussie.
- Modèle réel de test : Systran/faster-whisper-tiny, snapshot
  d90ca5fe260221311c53c58e660288d3deb8d356, CPU int8. Téléchargé dans models/,
  puis utilisé localement. Le modèle small par défaut n'a pas été évalué ici.
- **69 tests réussis, 0 échec, 0 ignoré**, dont **46 tests M1**, 3 nouveaux tests
  de temps et les 20 tests préexistants. Durée de la dernière suite : 19,192 s.
- Journal : [m1-test-results.txt](m1-test-results.txt).
- Intégrations réelles : CLI M0 → CLI M1 sur parole synthétique Windows en anglais ;
  mot "video" reconnu et au moins cinq mots horodatés ; audio nul sans hallucination ;
  offset audio de 500 ms ; priming AAC ; trou de PTS conservé sous forme de silence.
- Correction : tiny hallucine sur une piste entièrement nulle sans garde préalable.
  M1 contrôle donc les échantillons PCM strictement à zéro avant l'ASR ; un seul
  échantillon non nul suffit à laisser passer le signal. Aucun seuil de voix faible.
- Correction du fixture de trou audio : PCM/MOV avait aplati ses timestamps.
  Le test utilise AAC et vérifie que le trou existe avant d'évaluer M1.
- GPU et échecs CUDA : tests simulés, pas de validation matérielle NVIDIA.
- Limites : alignement ASR estimé ; précision sur corpus réel français/smartphone,
  bruit et hésitations à évaluer. Écriture M1 exclusive sans hard links, mais pas
  atomique face à une panne brutale du processus ou de la machine.
- À cette étape, M2 et les modules suivants n'étaient pas encore développés.
- M1 a ensuite été accepté explicitement par l'utilisateur le 19 septembre 2026.

## M2 — vérification du 19 septembre 2026

- M1 accepté avant ce développement ; M0 et M1 gelés. Les empreintes SHA-256 de
  leurs 33 fichiers de code, tests, documentation et contrats ont été comparées
  avant/après M2 : aucune modification.
- Deux nouveaux contrats : `cuts-1.0.0.json` et
  `time-map-speechcut-1.0.0.json`. Aucun changement des contrats M0/M1.
- Détections M2 : silences longs, pauses notables, fillers explicites,
  répétitions immédiates, reprises exactes de phrase et faux départs prudents.
- Politique par défaut : conserver 420 ms sur les silences longs ; pauses de
  850 à 1 200 ms conservées avec proposition de revue ; reprises de phrase et
  faux départs toujours soumis à revue.
- Correction issue du premier test : préserver les accents dans les comparaisons
  lexicales pour ne pas confondre `la` et `là`. Tolérance accentuelle limitée au
  dictionnaire fermé des fillers.
- **27 tests M2 réussis, 0 échec, 0 ignoré** sous Python 3.11.9.
- **96 tests complets réussis, 0 échec, 0 ignoré**, incluant les tests réels M1
  CPU/FFmpeg et les 69 tests antérieurs. Durée : 21,004 s.
- M2 ne lit et ne produit aucun média. Aucune preview générée. Les deux sorties
  JSON sont exclusives et liées par SHA-256 ; rollback si la seconde écriture échoue.
- Limites : détection fondée sur le texte et les écarts ASR, sans analyse acoustique
  des respirations ; heuristiques et seuils à évaluer sur parole française réelle.
- M3 et tous les modules suivants : aucun développement.

M2 a ensuite été accepté explicitement par l'utilisateur le 19 septembre 2026.

## M3 — vérification du 19 septembre 2026

- M2 accepté avant ce développement ; M0, M1 et M2 gelés. Les empreintes SHA-256
  de leurs 55 fichiers de code, tests, documentation, temps et contrats ont été
  comparées avant/après M3 : aucune modification.
- Deux nouveaux contrats : `edit-plan-1.0.0.json` et
  `time-map-smartedit-1.0.0.json`. Aucun contrat validé n'a été modifié.
- Analyse locale et déterministe : hook, introduction, sections/thèmes, conclusion,
  CTA, répétitions lexicales, formulations comparées et passages à faible contenu.
- Politique prudente : toutes les ambiguïtés sont `REVIEW`. Même les doublons exacts
  restent en revue par défaut ; leur suppression automatique exige une option explicite.
- Le plan ignore les mots déjà supprimés par le mapping M2. Le mapping M3 repart
  seulement des intervalles SOURCE conservés par M2 et ne peut pas les réintroduire.
- Corrections issues des tests/revue : conflit de nom avec `unittest.run`, validation
  des suppressions sur mapping vide, choix global unique pour les groupes de doublons,
  puis filtrage sémantique contre les coupes SpeechCut.
- **18 tests M3 réussis, 0 échec, 0 ignoré** sous Python 3.11.9.
- **114 tests complets réussis, 0 échec, 0 ignoré**, incluant les tests réels M1
  CPU/FFmpeg et toutes les non-régressions M0–M2. Durée : 21,117 s.
- M3 ne lit, ne produit et ne modifie aucun média.
- Limites : représentation lexicale explicable plutôt qu'embeddings ; synonymes sans
  termes communs, implicite, ironie et dépendance à la ponctuation ASR restent au backlog.
- M4 et tous les modules suivants : aucun développement.

M3 a ensuite été accepté explicitement par l'utilisateur le 20 septembre 2026.

## M4 — vérification du 20 septembre 2026

- M3 accepté avant ce développement ; M0 à M3 gelés. Les empreintes SHA-256 de
  leurs 76 fichiers suivis ont été comparées avant/après M4 : aucune modification.
- Nouveau contrat `camera-plan-1.0.0.json`, validé comme schéma JSON Schema
  Draft 2020-12. Aucun contrat validé M0–M3 n'a été modifié.
- Pipeline interne séparé : lecture des frames SOURCE conservées, détection
  visage/personne, tracking, calcul 9:16, lissage et sérialisation du plan.
- Le backend OpenCV v1 est CPU, local et remplaçable par protocole. Une demande
  CUDA produit un fallback explicite ou une erreur si ce fallback est interdit.
- Zoom naturel plafonné à 1,08 et plafond absolu à 1,15. Les groupes impossibles
  à contenir proprement en 9:16 sont signalés pour revue.
- **25 tests M4 réussis, 0 échec, 0 ignoré**, dont lecture/rotation OpenCV réelle.
- **137 tests complets réussis, 0 échec, 2 ignorés** sous Python 3.11. Les deux
  tests ignorés sont des intégrations M1 ASR qui exigent `AUTOREEL_TEST_MODEL` ;
  M1 est gelé et ses tests avaient déjà été validés avec le modèle local.
- Limites : Haar/HOG doit être évalué sur vidéos smartphone réelles ; recherche
  OpenCV approximative sur certains médias VFR ; GPU réel non validé.
- M5 et tous les modules suivants : aucun développement.

M4 a ensuite été accepté explicitement par l'utilisateur le 20 septembre 2026.

## M5 — vérification du 20 septembre 2026

- M4 accepté avant ce développement ; M0 à M4 gelés. Les empreintes SHA-256 de
  leurs 99 fichiers de code, tests, documentation et contrats ont été comparées
  avant/après M5 : aucune modification.
- Nouveau contrat `visual-plan-1.0.0.json`, validé comme JSON Schema Draft
  2020-12. Aucun contrat validé M0–M4 n'a été modifié.
- Pipeline séparé : analyse des passages SmartEdit, concepts visualisables,
  conversion SOURCE→CUT, sélection par valeur/densité et génération exclusive.
- Types produits : illustration, photo, B-roll, icône/graphique ou `NONE`.
  Chaque décision conserve intervalle SOURCE, position CUT disponible, concept,
  durée, priorité, confiance et raison explicite.
- Politique prudente : espacement par défaut de 3,5 s, deux visuels maximum par
  section, concepts ambigus en `REVIEW`, conflits de densité convertis en `NONE`.
- M5 ne lit aucun média, ne recherche et ne télécharge aucun asset. Le plan est
  déterministe et M6 reste seul responsable de la résolution future des demandes.
- **16 tests M5 réussis, 0 échec, 0 ignoré**.
- **153 tests complets réussis, 0 échec, 2 ignorés** sous Python 3.11. Les deux
  tests ignorés sont les intégrations M1 ASR exigeant `AUTOREEL_TEST_MODEL`, déjà
  validées avant le gel de M1.
- Limites : heuristiques lexicales à évaluer sur corpus français réel ; synonymes,
  références implicites et disponibilité/licence des assets restent hors M5 v1.
- M7 et tous les modules suivants : aucun développement.

M5 a ensuite été accepté explicitement par l'utilisateur le 20 septembre 2026.

## M7 — vérification du 20 septembre 2026

- M5 accepté avant ce développement ; M0 à M5 gelés. Les empreintes SHA-256 de
  leurs 117 fichiers de code, tests, documentation et contrats ont été comparées
  avant/après M7 : aucune modification.
- Nouveau contrat `sound-plan-1.0.0.json`, validé comme JSON Schema Draft
  2020-12. Aucun contrat validé M0–M5 n'a été modifié.
- Conversion SOURCE→CUT entière centralisée dans le nouveau composant partagé
  `core/timeline.py`; les événements situés dans des plages supprimées sont ignorés.
- Pipeline séparé : collecte, classification, scoring/priorisation, conflits et
  densité, puis génération exclusive de `sound_plan.json`.
- Événements couverts : hook, phrase forte, apparition visuelle, changement de
  section, zoom ponctuel, transition et concept important.
- Politique sobre : 3 s d'espacement, huit SFX maximum par fenêtre de 60 s,
  arbitrage unique dans une fenêtre de conflit de 300 ms et gains de −27 à −23 dB.
- Les candidats écartés restent traçables avec `type/status: NONE`; les cas
  intermédiaires restent `REVIEW`. Aucun fichier audio n'est recherché ou inséré.
- **27 tests M7 réussis, 0 échec, 0 ignoré**.
- **180 tests complets réussis, 0 échec, 2 ignorés** sous Python 3.11. Les deux
  tests ignorés sont les intégrations M1 ASR exigeant `AUTOREEL_TEST_MODEL`, déjà
  validées avant le gel de M1.
- Limites : classification et densité à évaluer à l'écoute sur des montages réels ;
  timbre, durée, licence et fichier SFX concret restent sous responsabilité future M6.
- M8 et M6 : aucun développement.

M7 a ensuite été accepté explicitement par l'utilisateur le 20 septembre 2026.

## M8 — vérification du 20 septembre 2026

- M7 accepté avant ce développement ; M0 à M7 gelés. Les empreintes SHA-256 de
  leurs 136 fichiers de code, tests, documentation et contrats ont été comparées
  avant/après M8 : aucune modification.
- Nouveau contrat `music-plan-1.0.0.json`, validé comme JSON Schema Draft
  2020-12. Aucun contrat validé M0–M7 n'a été modifié.
- Pipeline séparé : contexte, MUSIC/REVIEW/NONE, mood, région stable, niveaux,
  ducking/fades, conflits SFX et génération exclusive de `music_plan.json`.
- Politique voix prioritaire : −28 dB sous parole par défaut, configurable seulement
  de −30 à −25 dB ; remontée à −21 dB uniquement sur silence d'au moins 1,5 s.
- Les pauses de moins de 300 ms restent intégrées au ducking. Les pauses courtes
  restent `STABLE_BASE`; aucune automation ne suit chaque mot ou micro-événement.
- Les SFX actifs protègent ±600 ms contre les remontées musicales. Une seule région
  `STABLE_BED` couvre normalement le programme CUT, avec fades plafonnés.
- Les régions CUT conservent toutes leurs correspondances SOURCE, même à travers
  des coupes, via le nouveau composant partagé `core/time_ranges.py`.
- La demande d'asset contient mood, énergie et durée, sans titre, artiste, fichier,
  recherche, téléchargement, génération, mixage ou insertion.
- **20 tests M8 réussis, 0 échec, 0 ignoré**.
- **200 tests complets réussis, 0 échec, 2 ignorés** sous Python 3.11. Les deux
  tests ignorés sont les intégrations M1 ASR exigeant `AUTOREEL_TEST_MODEL`, déjà
  validées avant le gel de M1.
- Limites : niveaux et moods à évaluer à l'écoute ; loudness, licence, boucle et
  choix du morceau concret restent sous responsabilité future M6.
- M6 et tous les modules suivants : aucun développement.

M8 a ensuite été accepté explicitement par l'utilisateur le 20 septembre 2026.

## M6 — vérification du 20 septembre 2026

- M8 accepté avant ce développement ; tous les modules précédents gelés. Les
  empreintes SHA-256 de leurs 154 fichiers ont été comparées avant/après M6 :
  aucune modification.
- Nouveau contrat `assets-manifest-1.0.0.json`, validé comme JSON Schema Draft
  2020-12. Aucun contrat validé n'a été modifié.
- Pipeline séparé : collecte des demandes M5/M7/M8, index local, scoring,
  résolution, validation FFprobe/SHA-256 et publication exclusive du manifest.
- Six familles prises en charge : images, illustrations, B-roll, graphics/icônes,
  SFX et musique. Les sidecars `.asset.json` fournissent tags et type facultatif.
- Identifiants stables dérivés du type et du SHA-256 ; un même contenu est
  dédupliqué et réutilisé par plusieurs demandes.
- Les assets projet utilisent des chemins relatifs portables. Les chemins externes
  restent absolus et explicitement signalés.
- Les correspondances faibles restent `REVIEW`; l'absence de fichier local validé
  reste `UNRESOLVED`. Aucun chemin, fichier ou métadonnée n'est inventé.
- Métadonnées : dimensions/codec/durée pour les visuels et vidéos ; durée,
  sample rate, canaux et loudness facultative pour l'audio.
- **20 tests M6 réussis, 0 échec, 0 ignoré**, dont FFprobe réel sur WAV, PNG et MP4.
- **220 tests complets réussis, 0 échec, 2 ignorés** sous Python 3.11. Les deux
  tests ignorés sont les intégrations M1 ASR exigeant `AUTOREEL_TEST_MODEL`, déjà
  validées avant le gel de M1.
- Limites : scoring lexical dépendant des noms/tags ; loudness non mesurée en v1 ;
  aucun catalogue distant, téléchargement ou contenu généré.
- M9, M10 et M11 : aucun développement.

M6 a ensuite été accepté explicitement par l'utilisateur le 20 septembre 2026.

## M10 Timeline Compiler Pass A — vérification du 20 septembre 2026

- M0 à M8 acceptés avant ce développement et gelés. Les empreintes SHA-256 de
  leurs 176 fichiers ont été comparées avant/après M10 Pass A : aucune modification.
- Nouveau contrat `timeline-draft-1.0.0.json`; aucun contrat validé n'a été modifié.
- Six pistes fixes : V1 source, V2 visuels résolus, V3 réservée, A1 voix source,
  A2 musique et A3 SFX. La chronologie V1/A1 vient exclusivement du mapping M3.
- SOURCE, CUT et TIMELINE restent des coordonnées séparées. Les keyframes M4
  sont attachées aux clips V1 et ne créent aucun média.
- Seules les requêtes M6 `RESOLVED` sont matérialisées. `REVIEW` et `UNRESOLVED`
  restent traçables dans `unmaterialized`.
- Le compilateur rejette les provenances, mappings, durées, fichiers, types,
  pistes, overlaps et timestamps incohérents, sans inventer ni tronquer un edit.
- **20 tests M10 réussis, 0 échec, 0 ignoré**.
- **240 tests complets réussis, 0 échec, 2 ignorés** sous Python 3.11. Les deux
  tests ignorés sont les intégrations M1 ASR exigeant `AUTOREEL_TEST_MODEL`.
- M9 Captions, M10 Pass Final et M11 Resolve Builder : aucun développement.

M10 Pass A a ensuite été accepté par l'utilisateur sous réserve d'ajouter
`TimelineCompilerError` dans `video.py`. Cette correction isolée a été appliquée
et les 20 tests M10 ont réussi avant le gel définitif.

## M9 Captions — vérification du 20 septembre 2026

- Nouveau contrat `captions-1.0.0.json`; aucun contrat validé n'a été modifié.
- Projection des mots M1 entièrement conservés via les événements V1 de Pass A.
  Les mots supprimés ou coupés à une frontière ne réapparaissent pas.
- Chaque caption conserve texte et mots exacts, provenance transcript,
  SOURCE/CUT/TIMELINE et plusieurs `source_intervals` lorsqu'elle traverse une coupe.
- Découpage déterministe court : cible de quatre mots, maximum six, ponctuation,
  pause et petits mots isolés pris en compte, deux lignes maximum.
- Style déclaratif 9:16 et timings par mot, sans police, renderer, média ou Resolve.
- **5 tests M9 réussis, 0 échec, 0 ignoré**.
- **245 tests complets réussis, 0 échec, 2 ignorés** sous Python 3.11. Les deux
  tests ignorés sont les intégrations M1 ASR exigeant `AUTOREEL_TEST_MODEL`.
- M10 Pass Final et M11 Resolve Builder : aucun développement.

M9 a ensuite été accepté par l'utilisateur sous réserve que chaque entrée de
`lines` respecte réellement `maximum_characters_per_line`. La segmentation et
la séparation des lignes ont été corrigées sans refactorisation ; les 5 tests
M9 ont réussi avant son gel définitif.

## M10 Timeline Compiler Final — vérification du 20 septembre 2026

- Nouveau contrat `timeline-1.0.0.json` avec six pistes et
  `stage: timeline_compiler_final`; aucun contrat validé n'a été modifié.
- V1, V2, A1, A2, A3, `unmaterialized` et `diagnostics` sont copiés exactement
  depuis Pass A. V3 reçoit uniquement les événements `CAPTION` de M9.
- Texte, lignes, coordonnées SOURCE/CUT/TIMELINE, intervalles SOURCE, mots,
  style et provenance M9 sont repris sans resegmentation ni recalcul.
- Le chemin et le SHA-256 du draft référencé par M9 doivent désigner exactement
  l'entrée fournie. Les deux entrées sont revérifiées avant publication.
- Rejet des captions hors durée, overlaps, incohérences CUT/TIMELINE,
  projections SOURCE incompatibles avec V1 et événements V3 invalides.
- Publication exclusive de `timeline.json`; aucun média ni entrée n'est modifié.
- **6 tests M10 Final réussis**, en plus des **20 tests Pass A**.
- **251 tests complets réussis, 0 échec, 2 ignorés** sous Python 3.11. Les deux
  tests ignorés sont les intégrations M1 ASR exigeant `AUTOREEL_TEST_MODEL`.
- M11 Resolve Builder : aucun développement.

M10 Final attend la validation explicite de l'utilisateur avant M11.
