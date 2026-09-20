"""Language-light token normalization for explicit SpeechCut heuristics."""

import re
import unicodedata


FILLERS = frozenset({
    "euh", "heu", "hum", "hmm", "hm", "uh", "um", "erm", "ben", "bah",
})
TERMINAL_RE = re.compile(r"[.!?…]\s*$")


def normalize_token(text: str) -> str:
    folded = unicodedata.normalize("NFC", text.casefold())
    return "".join(char for char in folded if char.isalnum() or char in "'-")


def is_filler(text: str) -> bool:
    token = unicodedata.normalize("NFKD", normalize_token(text))
    accentless = "".join(char for char in token if not unicodedata.combining(char))
    return accentless in FILLERS


def ends_sentence(text: str) -> bool:
    return bool(TERMINAL_RE.search(text))
