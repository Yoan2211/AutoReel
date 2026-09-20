# Backlog

## M0 accepté — ne pas modifier sans bug bloquant démontré

- Tester un média smartphone HDR/HLG/HEVC réel (métadonnées, rotation, timestamps).
- Étudier la dépendance aux liens durs pour publier le manifest sur les volumes sans hard links.

Ces points ne bloquent pas M1, conformément à l'acceptation du 19 septembre 2026.

## M1 accepté — ne pas modifier sans bug bloquant démontré

- Évaluer la précision et les timestamps sur parole française réelle, notamment les
  hésitations, répétitions, voix faibles et environnements smartphone bruités.
- Valider l'exécution CUDA et le repli CPU sur un GPU NVIDIA réel compatible.

Ces points ne bloquent pas M2, conformément à l'acceptation du 19 septembre 2026.

## M2 accepté — ne pas modifier sans bug bloquant démontré

- Évaluer les seuils de pause, le lexique de fillers et les heuristiques de reprise
  sur un corpus de parole française réelle avec respirations naturelles.
- Comparer les décisions fondées sur les écarts ASR à une analyse acoustique de souffle.

Ces points ne bloquent pas M3, conformément à l'acceptation du 19 septembre 2026.

## M3 accepté — ne pas modifier sans bug bloquant démontré

- Évaluer la segmentation et les seuils lexicaux sur des transcriptions françaises réelles.
- Étudier un moteur d'embeddings local remplaçable pour synonymes, implicite et contexte long.

Ces points ne bloquent pas M4, conformément à l'acceptation du 20 septembre 2026.

## M4 accepté — ne pas modifier sans bug bloquant démontré

- Évaluer Haar/HOG sur des vidéos smartphone réelles : profils, occlusions,
  mouvements rapides, personnes éloignées et changements d'éclairage.
- Mesurer la précision de recherche temporelle OpenCV sur des sources VFR réelles.
- Évaluer un détecteur/tracker GPU local remplaçable sur matériel NVIDIA.

Ces points ne bloquent pas M5, conformément à l'acceptation du 20 septembre 2026.

## M5 accepté — ne pas modifier sans bug bloquant démontré

- Évaluer lexiques, seuils de confiance et densité sur des contenus français réels.
- Mesurer les faux positifs sur les concepts implicites, synonymes et formulations
  qui décrivent un visuel sans réellement justifier son insertion.
- Valider plus tard la disponibilité et les licences lors de la résolution M6.

Ces points ne bloquent pas M7, conformément à l'acceptation du 20 septembre 2026.

## M7 accepté — ne pas modifier sans bug bloquant démontré

- Évaluer à l'écoute la classification, les gains et la densité sur des Reels
  français réels, avec voix, musique et SFX représentatifs.
- Ajuster les fenêtres de conflit pour les transitions et animations complexes.
- Vérifier plus tard timbre, durée et licence lors de la résolution des assets M6.

Ces points ne bloquent pas M8, conformément à l'acceptation du 20 septembre 2026.

## M8 accepté — ne pas modifier sans bug bloquant démontré

- Évaluer à l'écoute les niveaux, fades, moods et remontées sur des contenus réels.
- Mesurer ultérieurement la loudness du morceau concret et vérifier les boucles en M6.
- Ajuster les zones de protection lorsque la durée réelle des SFX sera connue.

Ces points ne bloquent pas M6, conformément à l'acceptation du 20 septembre 2026.

## M6 accepté — ne pas modifier sans bug bloquant démontré

- Évaluer le scoring lexical sur une bibliothèque réelle, avec noms et sidecars
  multilingues, puis vérifier les licences en dehors du manifest technique.
- Ajouter une mesure de loudness optionnelle sans rendre la résolution dépendante
  d'un outil propriétaire.

Ces points ne bloquent pas M10 Pass A, conformément à l'acceptation du 20 septembre 2026.

## M9 accepté — ne pas modifier sans bug bloquant démontré

- Évaluer les seuils de pause, la longueur des groupes et la position verticale
  sur des vidéos françaises réelles avec débits de parole variés.
- Ajuster ultérieurement le style dans le renderer sans modifier le texte ni les
  timings produits par M9.

Ces points ne bloquent pas M10 Final, conformément à l'acceptation du 20 septembre 2026.
