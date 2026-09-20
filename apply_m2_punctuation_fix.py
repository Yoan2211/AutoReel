from pathlib import Path
import py_compile
import shutil

ROOT = Path(__file__).resolve().parent
target = ROOT / "modules" / "m2_speechcut" / "analyze.py"

if not target.is_file():
    print(f"ERREUR: fichier introuvable: {target}")
    input("Appuie sur Entrée pour fermer...")
    raise SystemExit(1)

text = target.read_text(encoding="utf-8")

old = (
'            token = normalize_token(raw["text"])\n'
'            if not token:\n'
'                raise SpeechCutError(f"Word has no lexical token: {raw[\'id\']}")\n'
'            words.append(Word(raw["id"], raw["start_us"], raw["end_us"], raw["text"], token, segment["id"]))\n'
)

new = (
'            token = normalize_token(raw["text"])\n'
'            if not token:\n'
'                # M1 peut produire un token horodaté composé uniquement de ponctuation.\n'
'                # Ce token n\'apporte aucune information lexicale à SpeechCut : on l\'ignore\n'
'                # tout en conservant les contrôles d\'ordre et d\'unicité.\n'
'                seen.add(raw["id"])\n'
'                previous_start = raw["start_us"]\n'
'                continue\n'
'            words.append(Word(raw["id"], raw["start_us"], raw["end_us"], raw["text"], token, segment["id"]))\n'
)

if new in text:
    print("Le correctif M2 est déjà installé.")
elif old not in text:
    print("ERREUR: la version locale de analyze.py ne correspond pas au correctif attendu.")
    print("Aucun fichier n'a été modifié.")
    input("Appuie sur Entrée pour fermer...")
    raise SystemExit(2)
else:
    backup = target.with_suffix(".py.before_punctuation_fix")
    if not backup.exists():
        shutil.copy2(target, backup)

    patched = text.replace(old, new, 1)
    target.write_text(patched, encoding="utf-8")

    try:
        py_compile.compile(str(target), doraise=True)
    except Exception:
        shutil.copy2(backup, target)
        print("ERREUR: le contrôle Python a échoué. Le fichier original a été restauré.")
        raise

    print("Correctif M2 installé avec succès.")
    print(f"Sauvegarde: {backup}")
    print()
    print("Tu peux retourner dans AutoReel et cliquer sur « Continuer le montage ».")

input("Appuie sur Entrée pour fermer...")
