import unittest

from modules.m2_speechcut.analyze import analyze, flatten_words
from modules.m2_speechcut.config import SpeechCutConfig
from modules.m2_speechcut.errors import SpeechCutError
from modules.m2_speechcut.tests.fixtures import transcript, word


class AnalyzeTests(unittest.TestCase):
    def kinds(self, words, **config):
        return analyze(transcript(words), SpeechCutConfig(**config))[1]

    def test_long_silence_keeps_natural_pause(self):
        decisions = analyze(transcript([word(0, " Bonjour", 100_000, 400_000),
                                        word(1, " suite", 2_000_000, 2_300_000)],
                                       duration_us=2_500_000), SpeechCutConfig())[1]
        silence = next(item for item in decisions if item.kind == "LONG_SILENCE")
        self.assertEqual((silence.start_us, silence.end_us), (610_000, 1_790_000))
        self.assertEqual(silence.retained_pause_us, 420_000)
        self.assertEqual(silence.disposition, "AUTO")

    def test_short_and_medium_pauses_are_kept(self):
        decisions = analyze(transcript([word(0, " Respire", 0, 300_000),
                                        word(1, " encore", 1_099_999, 1_300_000)],
                                       duration_us=1_500_000), SpeechCutConfig())[1]
        self.assertFalse(any(item.kind == "LONG_SILENCE" for item in decisions))

    def test_noticeable_pause_is_reviewed_but_not_auto_cut(self):
        decisions = analyze(transcript([word(0, " Respire", 0, 300_000),
                                        word(1, " encore", 1_200_000, 1_400_000)],
                                       duration_us=1_500_000), SpeechCutConfig())[1]
        pause = next(item for item in decisions if item.kind == "UNNECESSARY_PAUSE")
        self.assertEqual((pause.disposition, pause.confidence), ("REVIEW", "LOW"))

    def test_long_leading_and_trailing_silence_preserve_room_tone(self):
        decisions = analyze(transcript([word(0, " Centre", 2_000_000, 2_300_000)],
                                       origin_us=0, duration_us=4_000_000), SpeechCutConfig())[1]
        silences = [item for item in decisions if item.kind == "LONG_SILENCE"]
        self.assertEqual([(item.start_us, item.end_us) for item in silences],
                         [(0, 1_580_000), (2_720_000, 4_000_000)])

    def test_fillers_are_accent_and_case_tolerant(self):
        for token in (" Euh,", "HEU", " hum…", "Hmm", " bah"):
            decisions = self.kinds([word(0, " Avant", 0, 200_000),
                                    word(1, token, 300_000, 500_000),
                                    word(2, " après", 650_000, 900_000)])
            with self.subTest(token=token):
                filler = next(item for item in decisions if item.kind == "FILLER")
                self.assertEqual(filler.disposition, "AUTO")
                self.assertEqual(filler.word_ids, ("s000000w000001",))

    def test_lexical_umlaut_is_not_a_filler_and_long_filler_is_kept(self):
        decisions = self.kinds([word(0, " humble", 0, 300_000),
                                word(1, " euh", 400_000, 1_400_001)])
        self.assertFalse(any(item.kind == "FILLER" for item in decisions))

    def test_filler_can_require_review(self):
        decisions = self.kinds([word(0, " euh", 0, 200_000)], auto_apply_fillers=False)
        self.assertEqual(decisions[0].disposition, "REVIEW")

    def test_zero_duration_estimates_never_create_auto_word_cut(self):
        decisions = self.kinds([word(0, " euh", 100_000, 100_000),
                                word(1, " je", 200_000, 200_000),
                                word(2, " je", 250_000, 350_000)])
        self.assertFalse(any(item.kind in {"FILLER", "IMMEDIATE_REPETITION"}
                             for item in decisions))

    def test_immediate_repetition_removes_first_take(self):
        decisions = self.kinds([word(0, " je", 0, 100_000),
                                word(1, " je", 180_000, 280_000),
                                word(2, " parle", 320_000, 600_000)])
        repetition = next(item for item in decisions if item.kind == "IMMEDIATE_REPETITION")
        self.assertEqual((repetition.start_us, repetition.end_us), (0, 100_000))
        self.assertEqual(repetition.word_ids, ("s000000w000000", "s000000w000001"))

    def test_distant_or_different_repetition_is_kept(self):
        for words in ([word(0, " très", 0, 100_000), word(1, " très", 600_001, 700_000)],
                      [word(0, " la", 0, 100_000), word(1, " là", 150_000, 250_000)]):
            self.assertFalse(any(item.kind == "IMMEDIATE_REPETITION" for item in self.kinds(words)))

    def test_phrase_restart_is_review_only(self):
        tokens = [" je", " vais", " expliquer", " je", " vais", " expliquer", " cela"]
        words = [word(index, token, index * 200_000, index * 200_000 + 100_000)
                 for index, token in enumerate(tokens)]
        restart = next(item for item in self.kinds(words) if item.kind == "PHRASE_RESTART")
        self.assertEqual(restart.disposition, "REVIEW")
        self.assertEqual(restart.confidence, "MEDIUM")

    def test_false_start_is_review_only(self):
        first = [word(0, " Je", 0, 100_000, 0), word(1, " voulais", 150_000, 300_000, 0)]
        second = [word(0, " En fait", 500_000, 650_000, 1), word(1, " voici.", 700_000, 900_000, 1)]
        segments = [
            {"id": "s000000", "start_us": 0, "end_us": 300_000,
             "text": " Je voulais", "no_speech_probability": 0.01, "words": first},
            {"id": "s000001", "start_us": 500_000, "end_us": 900_000,
             "text": " En fait voici.", "no_speech_probability": 0.01, "words": second},
        ]
        decision = next(item for item in analyze(transcript(first + second, segments=segments), SpeechCutConfig())[1]
                        if item.kind == "FALSE_START")
        self.assertEqual((decision.disposition, decision.confidence), ("REVIEW", "LOW"))

    def test_complete_short_sentence_is_not_false_start(self):
        first = [word(0, " Voilà.", 0, 200_000, 0)]
        second = [word(0, " Ensuite", 400_000, 600_000, 1)]
        segments = [
            {"id": "s000000", "start_us": 0, "end_us": 200_000,
             "text": " Voilà.", "no_speech_probability": 0.01, "words": first},
            {"id": "s000001", "start_us": 400_000, "end_us": 600_000,
             "text": " Ensuite", "no_speech_probability": 0.01, "words": second},
        ]
        self.assertFalse(any(item.kind == "FALSE_START" for item in analyze(
            transcript(first + second, segments=segments), SpeechCutConfig())[1]))

    def test_invalid_word_stream_is_rejected(self):
        cases = [
            [word(0, " ok", 200, 100)],
            [word(0, " ok", 200, 300), word(1, " suite", 100, 150)],
            [word(0, " !!!", 0, 100)],
            [word(0, " ok", 0, 100), {**word(0, " encore", 200, 300)}],
        ]
        for words in cases:
            with self.subTest(words=words), self.assertRaises(SpeechCutError):
                flatten_words(transcript(words))
