"""Pure conservative heuristics over M1 word timing and text."""

from collections import defaultdict

from .config import SpeechCutConfig
from .errors import SpeechCutError
from .model import Candidate, Word
from .text import ends_sentence, is_filler, normalize_token


def flatten_words(transcript: dict) -> list[Word]:
    words: list[Word] = []
    seen: set[str] = set()
    previous_start: int | None = None
    for segment in transcript["segments"]:
        for raw in segment["words"]:
            if raw["id"] in seen:
                raise SpeechCutError(f"Duplicate word id: {raw['id']}")
            if raw["start_us"] > raw["end_us"]:
                raise SpeechCutError(f"Reversed word interval: {raw['id']}")
            if previous_start is not None and raw["start_us"] < previous_start:
                raise SpeechCutError("Words must be ordered in SOURCE time")
            token = normalize_token(raw["text"])
            if not token:
                raise SpeechCutError(f"Word has no lexical token: {raw['id']}")
            words.append(Word(raw["id"], raw["start_us"], raw["end_us"], raw["text"], token, segment["id"]))
            seen.add(raw["id"])
            previous_start = raw["start_us"]
    return words


def detect_pauses(words: list[Word], source_start_us: int, source_end_us: int,
                  config: SpeechCutConfig) -> list[Candidate]:
    result = []
    boundaries = [(source_start_us, words[0].start_us, (), (words[0].id,))]
    boundaries.extend((left.end_us, right.start_us, (left.id,), (right.id,))
                      for left, right in zip(words, words[1:]))
    boundaries.append((words[-1].end_us, source_end_us, (words[-1].id,), ()))
    for gap_start, gap_end, left_ids, right_ids in boundaries:
        gap = gap_end - gap_start
        if gap >= config.long_silence_us:
            # Preserve a natural pause symmetrically around the cut.
            trim_each_side = config.retained_pause_us // 2
            if not left_ids:  # Leading room tone: retain pause next to first speech.
                start, end = gap_start, gap_end - config.retained_pause_us
            elif not right_ids:  # Trailing room tone: retain pause after last speech.
                start, end = gap_start + config.retained_pause_us, gap_end
            else:
                start = gap_start + trim_each_side
                end = gap_end - (config.retained_pause_us - trim_each_side)
            if start < end:
                result.append(Candidate(
                    "LONG_SILENCE", start, end, "AUTO", "HIGH",
                    f"Reduce {gap} us inter-word silence to {config.retained_pause_us} us",
                    left_ids + right_ids, config.retained_pause_us,
                ))
        elif gap >= config.review_pause_us:
            result.append(Candidate(
                "UNNECESSARY_PAUSE", gap_start, gap_end, "REVIEW", "LOW",
                f"Pause of {gap} us is noticeable but retained for human review",
                left_ids + right_ids, gap,
            ))
    return result


def detect_fillers(words: list[Word], config: SpeechCutConfig) -> list[Candidate]:
    result = []
    for index, word in enumerate(words):
        if (not is_filler(word.text) or word.duration_us <= 0 or
                word.duration_us > config.filler_max_duration_us):
            continue
        left_bound = words[index - 1].end_us if index else word.start_us
        right_bound = words[index + 1].start_us if index + 1 < len(words) else word.end_us
        start = max(left_bound, word.start_us - config.filler_padding_us)
        end = min(right_bound, word.end_us + config.filler_padding_us)
        if start < end:
            result.append(Candidate(
                "FILLER", start, end,
                "AUTO" if config.auto_apply_fillers else "REVIEW", "HIGH",
                f"Isolated filler token: {word.token}", (word.id,),
            ))
    return result


def detect_immediate_repetitions(words: list[Word], config: SpeechCutConfig) -> list[Candidate]:
    result = []
    index = 0
    while index + 1 < len(words):
        first, second = words[index], words[index + 1]
        gap = second.start_us - first.end_us
        if first.duration_us > 0 and first.token == second.token and gap <= config.repetition_max_gap_us:
            # Remove the first take and keep the later, usually more committed one.
            result.append(Candidate(
                "IMMEDIATE_REPETITION", first.start_us, first.end_us,
                "AUTO" if config.auto_apply_repetitions else "REVIEW", "HIGH",
                f"Immediate repeated token: {first.token}", (first.id, second.id),
            ))
            index += 2
        else:
            index += 1
    return result


def _phrase_prefix_matches(words: list[Word], first: int, second: int, length: int) -> bool:
    return [w.token for w in words[first:first + length]] == [w.token for w in words[second:second + length]]


def detect_phrase_restarts(words: list[Word], config: SpeechCutConfig) -> list[Candidate]:
    result = []
    occupied: set[str] = set()
    for first in range(len(words)):
        maximum = min(config.phrase_restart_max_words, (len(words) - first) // 2)
        for length in range(maximum, config.phrase_restart_min_words - 1, -1):
            second = first + length
            if second + length > len(words):
                continue
            gap = words[second].start_us - words[second - 1].end_us
            ids = tuple(w.id for w in words[first:second + length])
            if (gap <= config.phrase_restart_max_gap_us and
                    _phrase_prefix_matches(words, first, second, length) and
                    not any(word_id in occupied for word_id in ids)):
                result.append(Candidate(
                    "PHRASE_RESTART", words[first].start_us, words[second - 1].end_us,
                    "REVIEW", "MEDIUM", f"Repeated phrase prefix of {length} words", ids,
                ))
                occupied.update(ids)
                break
    return result


def detect_false_starts(transcript: dict, words: list[Word], config: SpeechCutConfig) -> list[Candidate]:
    by_segment: dict[str, list[Word]] = defaultdict(list)
    for word in words:
        by_segment[word.segment_id].append(word)
    result = []
    for index, segment in enumerate(transcript["segments"][:-1]):
        group = by_segment[segment["id"]]
        following = by_segment[transcript["segments"][index + 1]["id"]]
        if (group and following and len(group) <= config.false_start_max_words and
                not ends_sentence(segment["text"]) and
                following[0].start_us - group[-1].end_us <= config.phrase_restart_max_gap_us):
            result.append(Candidate(
                "FALSE_START", group[0].start_us, group[-1].end_us,
                "REVIEW", "LOW", "Short non-terminal segment followed by a rapid restart",
                tuple(word.id for word in group),
            ))
    return result


def analyze(transcript: dict, config: SpeechCutConfig) -> tuple[list[Word], list[Candidate]]:
    words = flatten_words(transcript)
    if not words:
        return words, []
    candidates = (
        detect_pauses(words, transcript["analysis"]["origin_us"],
                      transcript["analysis"]["origin_us"] + transcript["analysis"]["duration_us"],
                      config) + detect_fillers(words, config) +
        detect_immediate_repetitions(words, config) +
        detect_phrase_restarts(words, config) + detect_false_starts(transcript, words, config)
    )
    return words, sorted(candidates, key=lambda item: (item.start_us, item.end_us, item.kind))
