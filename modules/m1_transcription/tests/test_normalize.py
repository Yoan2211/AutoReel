from dataclasses import replace
from pathlib import Path
import unittest

from modules.m1_transcription.audio import AnalysisAudio
from modules.m1_transcription.errors import TranscriptionError
from modules.m1_transcription.normalize import normalize
from modules.m1_transcription.tests.fixtures import recognition


class NormalizeTests(unittest.TestCase):
    def setUp(self):
        self.audio = AnalysisAudio(Path("unused.wav"), 500000, 3000000)
        self.raw = recognition()

    def test_invalid_timestamps_rejected_not_silently_clamped(self):
        segment = self.raw.segments[0]
        for start, end in [("-0.1", "1"), ("1", "0"), ("0", "4"), ("NaN", "1"),
                           ("0", "Infinity")]:
            raw = replace(self.raw, segments=(replace(segment, start_seconds=start, end_seconds=end),))
            with self.subTest(start=start, end=end), self.assertRaises(TranscriptionError):
                normalize(raw, self.audio)

    def test_missing_words_rejected(self):
        raw = replace(self.raw, segments=(replace(self.raw.segments[0], words=()),))
        with self.assertRaisesRegex(TranscriptionError, "word timestamps"):
            normalize(raw, self.audio)

    def test_invalid_word_and_probability_rejected(self):
        segment = self.raw.segments[0]
        word = segment.words[0]
        for changed in [replace(word, start_seconds="0"), replace(word, end_seconds="2"),
                        replace(word, text=" "), replace(word, probability=float("nan")),
                        replace(word, probability=True), replace(word, probability=1.1)]:
            raw = replace(self.raw, segments=(replace(segment, words=(changed,)),))
            with self.assertRaises(TranscriptionError):
                normalize(raw, self.audio)

    def test_zero_duration_and_overlap_are_preserved_and_flagged(self):
        segment = self.raw.segments[0]
        words = (replace(segment.words[0], end_seconds="0.6"), segment.words[1],
                 replace(segment.words[2], end_seconds="0.6"), segment.words[3])
        raw = replace(self.raw, segments=(replace(segment, words=words),))
        result, warnings = normalize(raw, self.audio)
        self.assertIn("ZERO_DURATION_WORD_ESTIMATE", warnings)
        self.assertIn("OVERLAPPING_WORD_ESTIMATES", warnings)
        self.assertEqual(result[0]["words"][0]["end_us"], 1100000)

    def test_word_order_is_not_repaired(self):
        segment = self.raw.segments[0]
        raw = replace(self.raw, segments=(replace(segment, words=tuple(reversed(segment.words))),))
        with self.assertRaisesRegex(TranscriptionError, "ordered"):
            normalize(raw, self.audio)

    def test_segments_must_be_ordered(self):
        segment = self.raw.segments[0]
        second = replace(segment, start_seconds="0", end_seconds="1.2")
        raw = replace(self.raw, segments=(segment, second))
        with self.assertRaisesRegex(TranscriptionError, "ordered"):
            normalize(raw, self.audio)
