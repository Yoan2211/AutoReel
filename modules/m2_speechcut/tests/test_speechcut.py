import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from modules.m2_speechcut import SpeechCutConfig, SpeechCutError, speechcut
from modules.m2_speechcut.contracts import validate
from modules.m2_speechcut.tests.fixtures import save, transcript, word


class SpeechCutTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.source = self.root / "transcript.json"
        self.cuts = self.root / "result" / "cuts.json"
        self.time_map = self.root / "result" / "time_map.json"
        self.value = transcript([
            word(0, " Bonjour", 100_000, 300_000),
            word(1, " euh", 500_000, 650_000),
            word(2, " je", 800_000, 900_000),
            word(3, " je", 1_000_000, 1_100_000),
            word(4, " continue", 2_600_000, 2_900_000),
        ], origin_us=-200_000, duration_us=4_000_000)
        save(self.source, self.value)

    def test_outputs_match_contracts_and_hash_chain(self):
        raw = self.source.read_bytes()
        cuts, time_map = speechcut(self.source, self.cuts, self.time_map)
        validate(cuts, "cuts-1.0.0.json")
        validate(time_map, "time-map-speechcut-1.0.0.json")
        self.assertEqual(cuts, json.loads(self.cuts.read_text(encoding="utf-8")))
        self.assertEqual(time_map, json.loads(self.time_map.read_text(encoding="utf-8")))
        self.assertEqual(self.source.read_bytes(), raw)
        self.assertEqual(cuts["source"]["transcript_sha256"], hashlib.sha256(raw).hexdigest())
        self.assertEqual(time_map["source"]["cuts_sha256"], hashlib.sha256(self.cuts.read_bytes()).hexdigest())
        self.assertEqual(cuts["time_domain"], "SOURCE")
        self.assertTrue(all(item["time_domain"] == "SOURCE" for item in cuts["decisions"]))
        self.assertTrue(all(item["source"]["time_domain"] == "SOURCE" and
                            item["target"]["time_domain"] == "CUT"
                            for item in time_map["mappings"]))

    def test_review_decisions_do_not_change_time_map(self):
        words = [word(i, token, i * 200_000, i * 200_000 + 100_000)
                 for i, token in enumerate([" je", " vais", " je", " vais"])]
        save(self.source, transcript(words, duration_us=1_000_000))
        cuts, time_map = speechcut(self.source, self.cuts, self.time_map,
                                   SpeechCutConfig(auto_apply_repetitions=False))
        self.assertTrue(any(item["kind"] == "PHRASE_RESTART" and item["disposition"] == "REVIEW"
                            for item in cuts["decisions"]))
        self.assertEqual(time_map["output_duration_us"], 1_000_000)

    def test_no_speech_is_identity_map_with_warning(self):
        save(self.source, transcript([], origin_us=500_000, duration_us=2_000_000))
        cuts, time_map = speechcut(self.source, self.cuts, self.time_map)
        self.assertEqual(cuts["decisions"], [])
        self.assertEqual(cuts["warnings"], ["NO_SPEECH_RECOGNIZED"])
        self.assertEqual(time_map["mappings"][0]["source"]["start_us"], 500_000)
        self.assertEqual(time_map["output_duration_us"], 2_000_000)

    def test_invalid_input_and_out_of_bounds_words_fail_without_outputs(self):
        cases = ["not json", "[]", json.dumps({**self.value, "schema_version": "2.0.0"})]
        for content in cases:
            self.source.write_text(content, encoding="utf-8")
            with self.assertRaises(SpeechCutError):
                speechcut(self.source, self.cuts, self.time_map)
            self.assertFalse(self.cuts.exists())
            self.assertFalse(self.time_map.exists())
        save(self.source, transcript([word(0, " hors", -1, 100)], origin_us=0, duration_us=1000))
        with self.assertRaisesRegex(SpeechCutError, "outside"):
            speechcut(self.source, self.cuts, self.time_map)

    def test_existing_outputs_and_input_alias_are_refused(self):
        self.cuts.parent.mkdir()
        self.cuts.write_text("existing", encoding="utf-8")
        with self.assertRaises(FileExistsError):
            speechcut(self.source, self.cuts, self.time_map)
        self.assertEqual(self.cuts.read_text(encoding="utf-8"), "existing")
        with self.assertRaises(FileExistsError):
            speechcut(self.source, self.source, self.time_map)
        with self.assertRaises(FileExistsError):
            speechcut(self.source, self.time_map, self.time_map)

    def test_second_output_failure_rolls_back_both(self):
        import modules.m2_speechcut.output as output_module
        original_fsync = output_module.os.fsync
        calls = 0
        def fail_second(fd):
            nonlocal calls
            calls += 1
            if calls == 2:
                raise OSError("disk full")
            return original_fsync(fd)
        with patch("modules.m2_speechcut.output.os.fsync", side_effect=fail_second):
            with self.assertRaisesRegex(OSError, "disk full"):
                speechcut(self.source, self.cuts, self.time_map)
        self.assertFalse(self.cuts.exists())
        self.assertFalse(self.time_map.exists())

    def test_configuration_validation(self):
        cases = [
            {"long_silence_us": 100, "retained_pause_us": 100},
            {"review_pause_us": 1_200_000},
            {"long_silence_us": True}, {"filler_padding_us": -1},
            {"phrase_restart_min_words": 1},
            {"phrase_restart_min_words": 5, "phrase_restart_max_words": 4},
            {"auto_apply_fillers": 1},
        ]
        for case in cases:
            with self.subTest(case=case), self.assertRaises(ValueError):
                SpeechCutConfig(**case)


class CliTests(unittest.TestCase):
    def test_missing_input_is_clean_error(self):
        result = subprocess.run([sys.executable, "-m", "modules.m2_speechcut",
                                 "missing.json", "cuts.json", "map.json"],
                                capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 1)
        self.assertIn("M2:", result.stderr)
        self.assertNotIn("Traceback", result.stderr)

    def test_success_writes_both_contracts(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source, cuts, time_map = root / "transcript.json", root / "cuts.json", root / "map.json"
            save(source, transcript([word(0, " Bonjour", 100_000, 300_000)],
                                    duration_us=500_000))
            result = subprocess.run([sys.executable, "-m", "modules.m2_speechcut",
                                     str(source), str(cuts), str(time_map)],
                                    capture_output=True, text=True, timeout=10)
            self.assertEqual(result.returncode, 0, result.stderr)
            validate(json.loads(cuts.read_text(encoding="utf-8")), "cuts-1.0.0.json")
            validate(json.loads(time_map.read_text(encoding="utf-8")),
                     "time-map-speechcut-1.0.0.json")
