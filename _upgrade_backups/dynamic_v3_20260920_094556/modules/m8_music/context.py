import re
import unicodedata


MOODS = (
    ("clean_modern_medical", {"santé", "medical", "médical", "médecin", "patient", "soin", "science"}),
    ("clean_modern_technology", {"technologie", "tech", "donnée", "données", "logiciel", "intelligence", "numérique"}),
    ("clean_modern_business", {"vente", "ventes", "entreprise", "client", "marché", "business", "stratégie"}),
    ("warm_minimal_story", {"histoire", "souvenir", "émotion", "famille", "parcours", "récit"}),
    ("clean_modern_educational", {"exemple", "étape", "conseil", "comprendre", "apprendre", "méthode"}),
)


def analyze(edit, visual):
    text = " ".join(item["text"] for item in edit["passages"])
    normalized = unicodedata.normalize("NFC", text.casefold())
    words = set(re.findall(r"[\w'-]+", normalized, re.UNICODE))
    ranked = []
    for index, (mood, lexicon) in enumerate(MOODS):
        ranked.append((len(words & lexicon), -index, mood))
    matches, _, mood = max(ranked)
    selected_visuals = sum(item["disposition"] != "NONE" for item in visual["requests"])
    energy = "MEDIUM" if selected_visuals >= 3 and mood not in ("clean_modern_medical", "warm_minimal_story") else "LOW"
    confidence = "HIGH" if matches >= 2 else "MEDIUM" if matches == 1 else "LOW"
    if matches == 0:
        mood = "clean_modern_neutral"
    reason = (f"Mood selected from {matches} explicit thematic term(s)"
              if matches else "No specific musical theme; neutral modern bed is safest")
    return mood, energy, confidence, reason
