import re
import unicodedata

from .model import Candidate


STOPWORDS = frozenset({"avec", "cette", "dans", "des", "est", "les", "pour", "que", "qui", "une", "vous", "votre", "mais", "sur", "par", "plus", "comme", "tout", "être", "avoir", "faire"})
GRAPHIC = frozenset({"chiffre", "chiffres", "pourcent", "pourcentage", "statistique", "graphique", "comparaison", "étape", "étapes", "liste", "trois", "deux", "quatre"})
PHOTO = frozenset({"photo", "portrait", "personne", "ville", "pays", "lieu", "monument", "produit", "objet"})
BROLL = frozenset({"marche", "marcher", "court", "courir", "cuisine", "cuisiner", "travaille", "travailler", "voyage", "voyager", "écran", "téléphone", "ordinateur", "atelier", "route"})
ILLUSTRATION = frozenset({"exemple", "imagine", "visualise", "concept", "mécanisme", "processus", "fonctionne", "architecture", "cycle"})


def tokens(text):
    normalized = unicodedata.normalize("NFC", text.casefold())
    return tuple(word for word in re.findall(r"[\w'-]+", normalized, re.UNICODE)
                 if len(word) > 2 and word not in STOPWORDS)


def detect(passage, section_id, section_terms, window, role_names):
    words = tokens(passage["text"])
    word_set = set(words)
    numeric = bool(re.search(r"\b\d+(?:[,.]\d+)?\s*%?\b", passage["text"]))
    media_type, score, signal = None, 0.0, ""
    if numeric or word_set & GRAPHIC:
        media_type, score, signal = "ICON_GRAPHIC", .9 if numeric else .82, "numeric or structured information"
    elif word_set & BROLL:
        media_type, score, signal = "BROLL", .83, "concrete action or environment"
    elif word_set & PHOTO:
        media_type, score, signal = "PHOTO", .8, "specific person, place or object"
    elif word_set & ILLUSTRATION:
        media_type, score, signal = "ILLUSTRATION", .72, "explanatory concept"
    elif "CTA" in role_names:
        media_type, score, signal = "ICON_GRAPHIC", .65, "call-to-action could benefit from a restrained icon"
    if media_type is None:
        return None
    themes = [term for term in section_terms if term in word_set]
    concept_terms = themes + [word for word in words if word not in themes]
    concept = " ".join(concept_terms[:4]) or passage["text"][:80].strip()
    if "HOOK" in role_names:
        score += .03
    return Candidate(passage["id"], section_id, *window, concept, media_type,
                     round(min(score, 1.0), 6),
                     f"Visual signal: {signal}; concept derived from passage and section terms")
