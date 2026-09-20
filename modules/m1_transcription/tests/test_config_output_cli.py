import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from modules.m1_transcription import TranscriptionConfig
from modules.m1_transcription.output import write_transcript


class ConfigTests(unittest.TestCase):
    def test_invalid_configuration(self):
        cases = [{"model": ""}, {"models_dir": ""}, {"ffmpeg": ""},
                 {"device": "gpu"}, {"cpu_fallback": 1}, {"allow_model_download": 1},
                 {"language": "French"}, {"language": 1}, {"audio_stream_index": True},
                 {"audio_stream_index": -1}, {"beam_size": 0}, {"cpu_threads": 1.5},
                 {"decode_timeout_s": -1}]
        for case in cases:
            with self.subTest(case=case), self.assertRaises(ValueError):
                TranscriptionConfig(**case)


class OutputTests(unittest.TestCase):
    def test_exclusive_creation_preserves_concurrent_file(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "result.json"
            write_transcript(path, {"text": "été"})
            before = path.read_bytes()
            with self.assertRaises(FileExistsError):
                write_transcript(path, {"text": "replacement"})
            self.assertEqual(path.read_bytes(), before)
            self.assertEqual(json.loads(before)["text"], "été")

    def test_failed_write_does_not_leave_partial_json(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "result.json"
            with patch("modules.m1_transcription.output.os.fsync", side_effect=OSError("disk error")):
                with self.assertRaises(OSError):
                    write_transcript(path, {"text": "test"})
            self.assertFalse(path.exists())


class CliTests(unittest.TestCase):
    def test_missing_manifest_is_clean_error(self):
        result = subprocess.run([sys.executable, "-m", "modules.m1_transcription",
                                 "missing-source.json", "unused-output.json"],
                                capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 1)
        self.assertIn("M1:", result.stderr)
        self.assertNotIn("Traceback", result.stderr)
