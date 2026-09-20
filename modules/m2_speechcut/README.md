# M2 SpeechCut — v1.0.0

## Responsabilité

M2 lit exclusivement le contrat JSON de M1 et publie deux contrats JSON :

- `cuts.json` : observations et décisions en temps `SOURCE` ;
- `time_map.json` : correspondance des intervalles conservés de `SOURCE` vers `CUT`,
  au stade `speechcut`.

M2 ne lit, ne décode, ne réencode et ne modifie aucun média. Il ne produit pas de
preview dans cette version. Une future preview restera un artefact de validation,
jamais une référence projet. M2 n'importe aucune implémentation M0 ou M1 : il valide
`transcript.json` contre `transcript-1.0.0.json` puis travaille sur ce contrat.

## API et CLI

```python
cuts, time_map = speechcut(
    "projects/demo/transcript.json",
    "projects/demo/cuts.json",
    "projects/demo/time_map.json",
    SpeechCutConfig(),
)
```

```powershell
.\.venv\Scripts\python.exe -m modules.m2_speechcut `
  "projects\demo\transcript.json" `
  "projects\demo\cuts.json" `
  "projects\demo\time_map.json"
```

Les trois chemins doivent être distincts. Les sorties existantes sont refusées.
Si l'écriture de la seconde sortie échoue, M2 retire les sorties qu'il vient de créer.
Une interruption brutale du processus peut toutefois laisser un fichier à examiner.

## Politique conservatrice

Les timestamps ASR sont des estimations. M2 ne prétend pas identifier une respiration
à partir du transcript seul. Il interprète uniquement les mots et leurs écarts.

| Détection | Défaut | Décision |
| --- | ---: | --- |
| Silence long | ≥ 1 200 000 µs | `AUTO`, réduit à 420 000 µs de pause |
| Pause notable | ≥ 850 000 et < 1 200 000 µs | `REVIEW`, conservée |
| Filler explicite | euh, heu, hum, hmm, hm, uh, um, erm, ben, bah | `AUTO`, configurable en `REVIEW` |
| Répétition immédiate exacte | même token, écart ≤ 450 000 µs | première occurrence `AUTO`, configurable en `REVIEW` |
| Phrase recommencée | préfixe exact de 2 à 6 mots, reprise ≤ 900 000 µs | `REVIEW` |
| Faux départ | segment non terminal de 1 à 4 mots, reprise ≤ 900 000 µs | `REVIEW` faible confiance |

Les silences de début et fin suivent la même règle, avec 420 000 µs de room tone
conservées près de la parole. Les silences internes gardent cette pause autour du
point de raccord. Les pauses sous 850 000 µs ne génèrent aucune proposition.

La normalisation respecte les accents pour les répétitions (`la` ≠ `là`). La liste
fermée des fillers accepte casse, ponctuation et variantes accentuelles. Une estimation
de mot de durée nulle ne déclenche jamais une coupe automatique de filler/répétition.

Les détections de faux départ et de reprise de phrase sont volontairement proposées
à la validation humaine : un transcript ne suffit pas à distinguer avec fiabilité une
répétition rhétorique, une correction utile ou un raté. M2 ne fait aucune analyse
sémantique et ne traite pas les répétitions éloignées ; M3 pourra prendre d'autres
décisions après validation de son propre contrat.

## Chevauchements

Les propositions sont toutes conservées dans `cuts.json`. Pour les seules décisions
`AUTO` qui se chevauchent, la priorité est : répétition immédiate, filler, silence.
La proposition non retenue devient `SUPPRESSED` et n'affecte pas `time_map.json`.
Les intervalles adjacents sont autorisés. Les décisions `REVIEW` ne modifient jamais
la time map.

## Contrat `cuts.json`

Schéma : [cuts-1.0.0.json](../../core/schemas/cuts-1.0.0.json).

- module `M2` version `1.0.0`, stage `speechcut`, domaine `SOURCE` ;
- empreintes du transcript exact et du média original référencé par M1 ;
- politique complète embarquée pour rendre le résultat reproductible ;
- décisions ordonnées avec type, disposition, confiance, raison, IDs de mots,
  `start_us`, `end_us`, `duration_us` en `SOURCE` ;
- résumé des propositions, applications, revues, suppressions par conflit et durée
  réellement retirée ;
- transcript sans parole : aucune décision et avertissement explicite.

Les IDs `cutNNNNNN` sont positionnels et déterministes pour un transcript, une version
et une configuration donnés. Ils ne sont pas des identités éditoriales persistantes.

## Contrat `time_map.json`

Schéma : [time-map-speechcut-1.0.0.json](../../core/schemas/time-map-speechcut-1.0.0.json).

Chaque mapping contient un intervalle semi-ouvert conservé :

```json
{
  "source": {"time_domain": "SOURCE", "start_us": 120000, "end_us": 900000},
  "target": {"time_domain": "CUT", "start_us": 0, "end_us": 780000}
}
```

Les décisions restent toutes ancrées en `SOURCE`. Les coordonnées `CUT` existent
uniquement dans la cible explicite de la correspondance. La carte couvre la durée
d'analyse audio déclarée par M1, y compris les silences de bord. Elle référence par
SHA-256 le fichier `cuts.json` exact, qui référence lui-même le transcript exact.
Une transcription sans parole produit une carte identité, pas une timeline vide.

## Configuration

`SpeechCutConfig` expose tous les seuils en microsecondes entières. Les contraintes
garantissent `retained_pause_us < review_pause_us < long_silence_us`. Les options
`auto_apply_fillers` et `auto_apply_repetitions` permettent de convertir ces familles
en `REVIEW`. La CLI expose les seuils de silence et les deux bascules de revue ; l'API
permet de régler toute la politique.

## Limites et backlog M2

- Les blancs sont inférés des timestamps de mots, sans détection acoustique de souffle.
- Les erreurs ou omissions ASR limitent toutes les heuristiques textuelles.
- Le lexique de fillers est volontairement court et explicite.
- Pas de stemming, similarité sémantique, diarisation ni détection multilingue avancée.
- Une preview vidéo/audio n'est pas implémentée.
- Les seuils doivent être évalués sur parole française réelle avant usage automatique
  à grande échelle ; la revue de `cuts.json` reste recommandée.

## Tests

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s modules/m2_speechcut/tests -t . -v
.\.venv\Scripts\python.exe -m unittest discover -v
```

Les 27 tests M2 couvrent chaque famille de détection, les accents, les mots de durée nulle,
les pauses de bord, la résolution des conflits, les domaines temporels, les empreintes,
les sorties exclusives, le rollback et la non-régression complète de M0/M1.
