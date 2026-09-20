import re
import unicodedata


STOPWORDS = frozenset({
    "a", "au", "aux", "avec", "ce", "ces", "dans", "de", "des", "du", "elle",
    "en", "et", "est", "il", "je", "la", "le", "les", "mais", "nous", "on",
    "ou", "par", "pas", "pour", "que", "qui", "se", "sur", "tu", "un", "une",
    "vous", "the", "a", "an", "and", "of", "to", "is", "in", "for", "you",
})
WEAK = frozenset({"peut-être", "peut", "genre", "disons", "environ", "probablement", "juste"})
CTA_PHRASES = ("abonne", "inscris", "clique", "partage", "commente", "lien en bio", "suis-moi", "dites-moi")
INTRO_MARKERS = ("aujourd'hui", "dans cette vidéo", "je vais", "on va", "voici")
CONCLUSION_MARKERS = ("en conclusion", "pour conclure", "en résumé", "finalement", "pour finir")


def normalize(text: str) -> str:
    return " ".join(re.findall(r"[\w'-]+", unicodedata.normalize("NFC", text.casefold()), re.UNICODE))


def lexical_tokens(text: str) -> tuple[str, ...]:
    return tuple(token for token in normalize(text).split() if token not in STOPWORDS and len(token) > 1)


def similarity(left: tuple[str, ...], right: tuple[str, ...]) -> float:
    a, b = set(left), set(right)
    return len(a & b) / len(a | b) if a or b else 0.0


def contains_any(text: str, phrases: tuple[str, ...]) -> bool:
    value = normalize(text)
    return any(phrase in value for phrase in phrases)
