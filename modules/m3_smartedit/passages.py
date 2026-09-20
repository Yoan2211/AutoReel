"""Build sentence-like semantic units while retaining original SOURCE bounds."""

from .errors import SmartEditError
from .model import Passage
from .text import WEAK, lexical_tokens, normalize


def _strength(text: str, tokens: tuple[str, ...]) -> float:
    normalized = normalize(text)
    weak_count = sum(normalized.split().count(term) for term in WEAK)
    lexical_density = min(1.0, len(set(tokens)) / 8) if tokens else 0.0
    assertive = 0.1 if any(char in text for char in ("!", "?")) else 0.0
    return round(max(0.0, min(1.0, 0.35 + lexical_density + assertive - weak_count * 0.15)), 6)


def _retained(word: dict, mappings: list[dict]) -> bool:
    if word["start_us"] == word["end_us"]:
        return any(item["source"]["start_us"] <= word["start_us"] < item["source"]["end_us"]
                   for item in mappings)
    return any(word["start_us"] < item["source"]["end_us"] and
               item["source"]["start_us"] < word["end_us"] for item in mappings)


def build_passages(transcript: dict, mappings: list[dict] | None = None) -> list[Passage]:
    raw_words = [word for segment in transcript["segments"] for word in segment["words"]]
    if mappings is not None:
        raw_words = [word for word in raw_words if _retained(word, mappings)]
    if not raw_words:
        return []
    passages, current = [], []
    for word in raw_words:
        if current and word["start_us"] < current[-1]["start_us"]:
            raise SmartEditError("Transcript words are unordered")
        current.append(word)
        if any(mark in word["text"] for mark in (".", "!", "?", "…")):
            passages.append(current)
            current = []
    if current:
        passages.append(current)
    result = []
    for index, group in enumerate(passages):
        text = "".join(word["text"] for word in group).strip()
        tokens = lexical_tokens(text)
        if not text:
            raise SmartEditError("Empty semantic passage")
        result.append(Passage(f"passage{index:06d}", group[0]["start_us"],
                              group[-1]["end_us"], text,
                              tuple(word["id"] for word in group), tokens,
                              _strength(text, tokens)))
    return result
