"""Transparent semantic planning heuristics; uncertain edits remain REVIEW."""

from .config import SmartEditConfig
from .model import Passage
from .text import CTA_PHRASES, CONCLUSION_MARKERS, INTRO_MARKERS, contains_any, normalize, similarity


def roles(passages: list[Passage]) -> list[dict]:
    if not passages:
        return []
    result = [{"role": "HOOK", "passage_id": passages[0].id, "confidence": "MEDIUM",
               "reason": "First spoken passage; candidate opening hook"}]
    intro = next((item for item in passages[:3] if contains_any(item.text, INTRO_MARKERS)), None)
    if intro:
        result.append({"role": "INTRODUCTION", "passage_id": intro.id, "confidence": "HIGH",
                       "reason": "Explicit introduction marker"})
    elif len(passages) > 1:
        result.append({"role": "INTRODUCTION", "passage_id": passages[1].id,
                       "confidence": "LOW", "reason": "Early passage without explicit marker"})
    conclusion = next((item for item in reversed(passages[-3:])
                       if contains_any(item.text, CONCLUSION_MARKERS)), passages[-1])
    result.append({"role": "CONCLUSION", "passage_id": conclusion.id,
                   "confidence": "HIGH" if contains_any(conclusion.text, CONCLUSION_MARKERS) else "LOW",
                   "reason": "Explicit conclusion marker" if contains_any(conclusion.text, CONCLUSION_MARKERS)
                   else "Final spoken passage; candidate conclusion"})
    for item in passages:
        if contains_any(item.text, CTA_PHRASES):
            result.append({"role": "CTA", "passage_id": item.id, "confidence": "HIGH",
                           "reason": "Explicit call-to-action wording"})
    return result


def sections(passages: list[Passage], config: SmartEditConfig) -> list[dict]:
    if not passages:
        return []
    groups = [[passages[0]]]
    for passage in passages[1:]:
        previous_tokens = tuple(token for item in groups[-1] for token in item.tokens)
        if (len(groups[-1]) >= config.max_section_sentences or
                similarity(previous_tokens, passage.tokens) < config.topic_similarity_threshold):
            groups.append([passage])
        else:
            groups[-1].append(passage)
    result = []
    for index, group in enumerate(groups):
        frequency = {}
        for passage in group:
            for token in passage.tokens:
                frequency[token] = frequency.get(token, 0) + 1
        themes = sorted(frequency, key=lambda token: (-frequency[token], token))[:3]
        result.append({"id": f"section{index:06d}", "title": " / ".join(themes) or "Sans thème lexical",
                       "theme_terms": themes, "passage_ids": [item.id for item in group],
                       "source_start_us": group[0].source_start_us,
                       "source_end_us": group[-1].source_end_us})
    return result


def decisions(passages: list[Passage], config: SmartEditConfig) -> list[dict]:
    result, paired = [], set()
    exact_groups = {}
    for passage in passages:
        exact_groups.setdefault(normalize(passage.text), []).append(passage)
    for group in exact_groups.values():
        if len(group) < 2:
            continue
        preferred = max(group, key=lambda item: (item.strength, -item.source_start_us))
        for weaker in group:
            if weaker.id == preferred.id:
                continue
            result.append({
                "id": f"decision{len(result):06d}", "kind": "EXACT_DUPLICATE",
                "disposition": "AUTO_REMOVE" if config.auto_remove_exact_duplicates else "REVIEW",
                "confidence": "HIGH", "source_start_us": weaker.source_start_us,
                "source_end_us": weaker.source_end_us,
                "passage_ids": [weaker.id, preferred.id],
                "preferred_passage_id": preferred.id, "similarity": 1.0,
                "reason": f"Exact duplicate; retain strongest passage {preferred.id}",
            })
            paired.add(weaker.id)
    for left_index, left in enumerate(passages):
        for right in passages[left_index + 1:]:
            score = similarity(left.tokens, right.tokens)
            exact = normalize(left.text) == normalize(right.text)
            if exact or score < config.semantic_similarity_threshold:
                continue
            preferred, weaker = (right, left) if right.strength > left.strength else (left, right)
            margin = abs(preferred.strength - weaker.strength)
            result.append({
                "id": f"decision{len(result):06d}", "kind": "SEMANTIC_REPETITION",
                "disposition": "REVIEW", "confidence": "MEDIUM",
                "source_start_us": weaker.source_start_us, "source_end_us": weaker.source_end_us,
                "passage_ids": [left.id, right.id], "preferred_passage_id": preferred.id,
                "similarity": round(score, 6),
                "reason": f"Prefer {preferred.id}; strength {preferred.strength:.3f} vs {weaker.strength:.3f}",
            })
            paired.add(weaker.id)
            if margin >= config.weak_formulation_margin:
                result.append({
                    "id": f"decision{len(result):06d}", "kind": "WEAKER_FORMULATION",
                    "disposition": "REVIEW", "confidence": "MEDIUM",
                    "source_start_us": weaker.source_start_us, "source_end_us": weaker.source_end_us,
                    "passage_ids": [weaker.id, preferred.id], "preferred_passage_id": preferred.id,
                    "similarity": round(score, 6),
                    "reason": f"Semantically related alternative scores {margin:.3f} stronger",
                })
    for passage in passages:
        if not passage.tokens and passage.id not in paired:
            result.append({
                "id": f"decision{len(result):06d}", "kind": "POTENTIALLY_REMOVABLE",
                "disposition": "REVIEW", "confidence": "LOW",
                "source_start_us": passage.source_start_us, "source_end_us": passage.source_end_us,
                "passage_ids": [passage.id], "preferred_passage_id": None, "similarity": 0.0,
                "reason": "Passage contains no informative lexical terms",
            })
    return result
