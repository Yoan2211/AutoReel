# M3 SmartEdit — v1.0.0

M3 analyse `transcript.json`, `cuts.json` et le `time_map.json` SpeechCut. Il publie
`edit_plan.json` et un mapping `SOURCE → CUT` au stade `smartedit`. Il ne lit, ne
décode et ne modifie aucun média. Il ne dépend d'aucune implémentation M0–M2 : les
trois entrées sont validées par leurs schémas et reliées par leurs SHA-256.
Avant l'analyse, les mots sont filtrés contre les intervalles SOURCE conservés par
le mapping SpeechCut ; une formulation déjà coupée par M2 ne peut donc devenir hook,
section, conclusion ou décision M3.

## Analyse et prudence

Le moteur v1 est local, déterministe et explicable. Il segmente les mots M1 en
passages à la ponctuation, puis calcule une représentation lexicale après retrait
d'un petit ensemble de mots-outils français et anglais.

- `HOOK` : premier passage, confiance moyenne car la position seule ne prouve pas
  la qualité du hook ;
- `INTRODUCTION` : marqueurs explicites (`aujourd'hui`, `je vais`, etc.), sinon
  second passage avec faible confiance ;
- sections/thèmes : regroupement adjacent par recouvrement lexical, titre composé
  des trois termes dominants ;
- `CONCLUSION` : marqueur explicite, sinon dernier passage avec faible confiance ;
- `CTA` : formulations explicites comme `abonne`, `clique`, `partage`, `commente` ;
- répétitions : doublon textuel exact ou recouvrement lexical au-dessus du seuil ;
- formulation faible : deux passages proches dont le score de densité/assertivité
  diffère suffisamment ;
- passage potentiellement supprimable : aucune information lexicale après filtrage.

Cette analyse n'est pas un modèle de compréhension générale : synonymes sans mots
communs, ironie, implicite et contexte long peuvent lui échapper. Les scores servent
à justifier et trier des propositions, pas à certifier une intention éditoriale.

Par défaut, **aucune décision sémantique ne supprime de matière**. Les répétitions,
formulations faibles et passages potentiellement supprimables sont `REVIEW`. Seul
un doublon textuel exact peut devenir `AUTO_REMOVE`, avec l'option explicite
`auto_remove_exact_duplicates=True` ou `--auto-remove-exact-duplicates`. Pour un
groupe de plusieurs doublons, M3 choisit une seule formulation préférée et retire
au plus les autres occurrences.

## Contrats

[edit-plan-1.0.0.json](../../core/schemas/edit-plan-1.0.0.json) contient :

- les chemins et empreintes exactes des trois entrées et du média référencé ;
- la politique complète ;
- chaque passage avec `source_start_us`, `source_end_us`, texte, mots et score ;
- rôles narratifs, sections/thèmes, décisions justifiées et passage préféré ;
- un résumé séparant revues et suppressions automatiques.

[time-map-smartedit-1.0.0.json](../../core/schemas/time-map-smartedit-1.0.0.json)
référence l'empreinte exacte du plan. M3 repart exclusivement des intervalles SOURCE
conservés par M2, soustrait les suppressions M3 automatiques, puis recompresse le
domaine CUT. Il ne peut pas réintroduire un intervalle déjà supprimé par SpeechCut.
Les bornes SOURCE restent présentes dans chaque mapping ; les coordonnées CUT sont
isolées dans la cible au domaine déclaré `CUT`.

Si aucune suppression M3 n'est automatique, le contenu SOURCE du mapping M2 est
reproduit et seule la provenance/stage change. Les décisions `REVIEW` ne changent
jamais le mapping.

## API et CLI

```python
plan, time_map = smartedit(
    "transcript.json", "cuts.json", "time_map_speechcut.json",
    "edit_plan.json", "time_map_smartedit.json", SmartEditConfig(),
)
```

```powershell
.\.venv\Scripts\python.exe -m modules.m3_smartedit `
  transcript.json cuts.json time_map_speechcut.json `
  edit_plan.json time_map_smartedit.json
```

Les cinq chemins doivent être distincts et les sorties ne doivent pas exister. Une
erreur pendant la seconde écriture retire les sorties créées par cette exécution.
Comme M1/M2, une panne brutale peut laisser un fichier à examiner manuellement.

## Configuration

- similarité sémantique lexicale : `0.72` ;
- seuil de continuité thématique : `0.18` ;
- quatre passages maximum par section ;
- marge de formulation faible : `0.15` ;
- suppression automatique des doublons exacts : désactivée.

Tous les seuils sont embarqués dans `edit_plan.json`. Les IDs sont déterministes et
positionnels pour une même version, configuration et entrée.

## Tests et limites

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s modules/m3_smartedit/tests -t . -v
.\.venv\Scripts\python.exe -m unittest discover -v
```

Les tests couvrent rôles, CTA, thèmes, répétitions, formulation préférée, prudence
par défaut, suppression opt-in, groupes de doublons, chaîne d'empreintes, refus des
écrasements, rollback et recalcul du mapping sans réintroduire les coupes M2.

À évaluer sur corpus français réel : ponctuation ASR, synonymes, qualité des hooks,
seuils de thèmes et détection des CTA moins explicites. Une future version pourra
brancher un moteur d'embeddings local derrière un contrat propre ; ce n'est pas
introduit silencieusement dans le contrat v1.
