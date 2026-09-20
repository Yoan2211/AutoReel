"""Validate ASR estimates and express every timestamp in original SOURCE time."""

import math

from core.time import seconds_to_timestamp_us
from .audio import AnalysisAudio
from .backend import Recognition
from .errors import TranscriptionError


def _probability(value: float) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TranscriptionError("Invalid ASR probability")
    if not math.isfinite(value) or not 0 <= value <= 1:
        raise TranscriptionError("ASR probability must be finite and between zero and one")
    return float(value)


def normalize(recognition: Recognition, audio: AnalysisAudio) -> tuple[list[dict], list[str]]:
    warnings = list(recognition.warnings)
    segments = []
    previous_start = audio.origin_us
    previous_word_start = audio.origin_us
    previous_word_end = audio.origin_us

    def interval(start: str, end: str) -> tuple[int, int]:
        try:
            start_us = seconds_to_timestamp_us(start, audio.origin_us)
            end_us = seconds_to_timestamp_us(end, audio.origin_us)
        except ValueError as exc:
            raise TranscriptionError(f"Invalid ASR timestamp: {exc}") from exc
        if not audio.origin_us <= start_us <= end_us <= audio.origin_us + audio.duration_us:
            raise TranscriptionError("ASR timestamps outside analysis audio bounds or reversed")
        return start_us, end_us

    for segment_index, segment in enumerate(recognition.segments):
        start, end = interval(segment.start_seconds, segment.end_seconds)
        if start < previous_start:
            raise TranscriptionError("ASR segments are not ordered")
        previous_start = start
        if not segment.text.strip() or not segment.words:
            raise TranscriptionError("ASR segment lacks text or word timestamps")
        words = []
        for word_index, word in enumerate(segment.words):
            word_start, word_end = interval(word.start_seconds, word.end_seconds)
            if not start <= word_start <= word_end <= end:
                raise TranscriptionError("ASR word lies outside its segment")
            if word_start < previous_word_start:
                raise TranscriptionError("ASR words are not ordered")
            if not word.text.strip():
                raise TranscriptionError("ASR word text is empty")
            if word_start < previous_word_end:
                warnings.append("OVERLAPPING_WORD_ESTIMATES")
            if word_start == word_end:
                warnings.append("ZERO_DURATION_WORD_ESTIMATE")
            previous_word_start, previous_word_end = word_start, word_end
            words.append({"id": f"s{segment_index:06d}w{word_index:06d}",
                          "start_us": word_start, "end_us": word_end,
                          "text": word.text, "probability": _probability(word.probability)})
        segments.append({"id": f"s{segment_index:06d}", "start_us": start, "end_us": end,
                         "text": segment.text,
                         "no_speech_probability": _probability(segment.no_speech_probability),
                         "words": words})
    if not segments:
        warnings.append("NO_SPEECH_RECOGNIZED")
    _probability(recognition.language_probability)
    return segments, sorted(set(warnings))
