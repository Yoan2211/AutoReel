# M9 Captions 1.0.0

M9 transforme les mots horodatés du transcript M1 en décisions de sous-titrage
pour formats verticaux. Il utilise V1 de `timeline_draft.json` comme autorité de
projection et ne modifie aucun média ni aucune timeline.

## Contrat

Entrées : `transcript.json` M1 et `timeline_draft.json` M10 Pass A. M9 vérifie
leur schéma, leur provenance par l'edit plan référencé et l'identité du média
SOURCE. La sortie exclusive `captions.json` respecte
`core/schemas/captions-1.0.0.json`.

Un mot doit être entièrement contenu dans un événement V1 conservé. Un mot
supprimé ou traversant une frontière de coupe n'est jamais réintroduit. Chaque
caption conserve les mots exacts de M1, leurs coordonnées SOURCE/CUT/TIMELINE,
sa provenance et ses `source_intervals`. Plusieurs intervalles sont conservés
quand une caption traverse une coupe SOURCE.

Le découpage déterministe vise quatre mots, avec deux à six mots en général et
un maximum absolu de six. La ponctuation forte, les pauses d'au moins 450 ms et
la limite de mots déclenchent une coupure. Un petit mot isolé est rattaché à un
groupe voisin lorsque la limite le permet. `lines` propose au plus deux lignes
sans reformuler `text`.

Le style est une indication structurée : zone basse sûre en 9:16, centrage,
présentation moderne lisible, animation subtile ou absente et timings par mot
pour un futur surlignage. M9 ne charge aucune police et ne rend aucun graphique.

```powershell
.\.venv\Scripts\python.exe -m modules.m9_captions transcript.json timeline_draft.json captions.json
```
