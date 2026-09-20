# M4 AutoCam — v1.0.0

M4 lit le manifest M0 et le mapping final M3, décode des images de la vidéo
**SOURCE originale** uniquement aux timestamps conservés, puis publie
`camera_plan.json`. Il ne réencode, ne produit et ne modifie aucun média. Il ne
modifie pas non plus les décisions SpeechCut/SmartEdit.

## Étapes isolées

1. `frames.py` échantillonne chaque intervalle SOURCE conservé et applique la
   rotation déclarée par M0 en mémoire ;
2. `detector.py` détecte d'abord les visages avec Haar, puis les personnes avec
   HOG si aucun visage n'est trouvé ;
3. `tracking.py` associe les détections successives et conserve brièvement une
   position prédite lors d'une perte temporaire ;
4. `framing.py` calcule une fenêtre 9:16 qui englobe les sujets, ajoute du
   dégagement au-dessus de la tête et limite le zoom ;
5. `smoothing.py` amortit centre et zoom et ne publie une keyframe que lors d'un
   changement utile ou au délai de garde ;
6. `autocam.py` valide et écrit exclusivement `camera_plan.json`.

Les interfaces `FrameProvider` et `SubjectDetector` sont des protocoles. Un
détecteur ou tracker plus avancé peut donc être substitué sans changer le contrat
de sortie ni lire les détails internes d'un autre module.

## Contrat

[camera-plan-1.0.0.json](../../core/schemas/camera-plan-1.0.0.json) contient les
empreintes du manifest M0, du mapping M3 et du média SOURCE, la géométrie encodée
et orientée, le moteur, toute la politique de cadrage, puis des plans SOURCE.
Chaque plan conserve `source_start_us` et `source_end_us`. Ses keyframes portent
`source_us`, centre normalisé, zoom, rectangle de crop en pixels et IDs de sujets.

M4 vérifie l'identité chemin + SHA-256 entre M0 et M3, puis la taille et le SHA-256
du média avant et après l'analyse. Une frame fournie dans un passage supprimé est
refusée. La sortie existante n'est jamais écrasée.

Le crop cible est toujours 1080×1920. Le zoom naturel est plafonné à 1,08. Un
visage exceptionnellement petit peut atteindre 1,15, plafond absolu du contrat.
Plusieurs personnes trop éloignées produisent
`SUBJECTS_EXCEED_VERTICAL_FRAME` pour revue plutôt qu'un zoom agressif.

## Backend et exécution

```powershell
.\.venv\Scripts\python.exe -m pip install -e ".[autocam]"
.\.venv\Scripts\python.exe -m modules.m4_autocam `
  projects\demo\source.json projects\demo\time_map_smartedit.json `
  projects\demo\camera_plan.json --device auto
```

Le backend OpenCV v1 (Haar + HOG) fonctionne sur CPU. `--device cuda` bascule
explicitement sur CPU avec l'avertissement `CPU_FALLBACK`; l'option
`--no-cpu-fallback` refuse alors l'exécution. Un backend GPU ultérieur peut être
injecté derrière `SubjectDetector`.

## Tests et limites

```powershell
.\.venv\Scripts\python.exe -m pytest modules/m4_autocam/tests -q
.\.venv\Scripts\python.exe -m pytest -q
```

Les tests couvrent sujet fixe ou mobile, deux personnes, perte temporaire,
exclusion des passages coupés, paysage, portrait, rotation, stabilité, plafonds
de zoom, contrats, intégrité SOURCE, non-écrasement et backend OpenCV réel.

Haar/HOG est un socle local et gratuit, pas un détecteur moderne : profils,
occlusions, très petits visages, mouvements rapides et groupes éloignés devront
être évalués sur vidéos smartphone réelles. La recherche OpenCV par timestamp est
approximative sur certaines vidéos à fréquence variable ; les décisions restent
cependant exprimées dans les timestamps SOURCE demandés et aucune image décodée
n'est conservée comme référence.
