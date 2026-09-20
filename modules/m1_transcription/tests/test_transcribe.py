from dataclasses import replace
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

from modules.m1_transcription import TranscriptionConfig, TranscriptionError, transcribe
from modules.m1_transcription.audio import AnalysisAudio
from modules.m1_transcription.contracts import validate_contract
from modules.m1_transcription.tests.fixtures import recognition, save_manifest, source_manifest


class TranscribeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.source = self.root / "vidéo originale.mov"
        self.source.write_bytes(b"source bytes, never edited")
        self.manifest = self.root / "source.json"
        self.data = source_manifest(self.source)
        save_manifest(self.manifest, self.data)
        self.output = self.root / "result" / "transcript.json"
        self.backend = Mock()
        self.backend.recognize.return_value = recognition()
        self.analysis_path = None

    def extract(self, source, stream, destination, config):
        self.assertEqual(source, self.source)
        self.analysis_path = destination
        destination.write_bytes(b"temporary analysis audio")
        return AnalysisAudio(destination, stream["start_us"], 3000000)

    def run_m1(self, config=None):
        with patch("modules.m1_transcription.transcribe.extract_audio", side_effect=self.extract):
            return transcribe(self.manifest, self.output, config, backend=self.backend)

    def test_contract_original_identity_and_verbatim_repetitions(self):
        before = self.source.read_bytes(), self.manifest.read_bytes()
        result = self.run_m1()
        validate_contract(result, "transcript-1.0.0.json")
        self.assertEqual(result["time_domain"], "SOURCE")
        self.assertEqual(result["segments"][0]["start_us"], 600000)
        self.assertEqual(result["segments"][0]["words"][0]["end_us"], 800000)
        self.assertEqual(result["text"], "Euh, je je teste.")
        self.assertEqual(result["source"]["sha256"], self.data["source"]["sha256"])
        self.assertEqual(result, json.loads(self.output.read_text(encoding="utf-8")))
        self.assertEqual(before, (self.source.read_bytes(), self.manifest.read_bytes()))
        self.assertFalse(self.analysis_path.exists())
        self.assertNotIn(str(self.analysis_path), self.output.read_text(encoding="utf-8"))

    def test_negative_source_origin(self):
        self.data["source"]["audio"][0]["start_us"] = -500000
        save_manifest(self.manifest, self.data)
        result = self.run_m1()
        self.assertEqual(result["segments"][0]["start_us"], -400000)

    def test_empty_recognition_is_explicit(self):
        self.backend.recognize.return_value = replace(recognition(), segments=())
        result = self.run_m1()
        self.assertEqual(result["status"], "no_speech_recognized")
        self.assertEqual(result["text"], "")
        self.assertIn("NO_SPEECH_RECOGNIZED", result["warnings"])

    def test_no_audio_and_ambiguous_audio_fail_before_decode(self):
        for audio in [[], self.data["source"]["audio"] + [
            {**self.data["source"]["audio"][0], "stream_index": 2}]]:
            self.data["source"]["audio"] = audio
            save_manifest(self.manifest, self.data)
            with self.assertRaises(TranscriptionError):
                self.run_m1()
        self.backend.recognize.assert_not_called()
        self.assertFalse(self.output.exists())

    def test_explicit_audio_selection(self):
        self.data["source"]["audio"].append(
            {**self.data["source"]["audio"][0], "stream_index": 2, "start_us": 2000000})
        save_manifest(self.manifest, self.data)
        result = self.run_m1(TranscriptionConfig(audio_stream_index=2))
        self.assertEqual(result["source"]["audio_stream_index"], 2)
        self.assertEqual(result["segments"][0]["start_us"], 2100000)

    def test_nonexistent_audio_selection(self):
        with self.assertRaisesRegex(TranscriptionError, "not in"):
            self.run_m1(TranscriptionConfig(audio_stream_index=99))

    def test_source_hash_mismatch_before_asr(self):
        original = self.source.read_bytes()
        self.source.write_bytes(b"x" * len(original))
        with self.assertRaisesRegex(TranscriptionError, "identity"):
            self.run_m1()
        self.backend.recognize.assert_not_called()
        self.assertFalse(self.output.exists())

    def test_source_size_mismatch(self):
        self.source.write_bytes(b"x")
        with self.assertRaisesRegex(TranscriptionError, "size"):
            self.run_m1()

    def test_source_modified_during_asr_rejected(self):
        def change(*args):
            self.source.write_bytes(b"changed")
            return recognition()
        self.backend.recognize.side_effect = change
        with self.assertRaisesRegex(TranscriptionError, "changed"):
            self.run_m1()
        self.assertFalse(self.analysis_path.exists())
        self.assertFalse(self.output.exists())

    def test_invalid_manifest_and_version_fail_early(self):
        for content in ["not json", "[]", '{"source": NaN}',
                        json.dumps({**self.data, "schema_version": "2.0.0"})]:
            self.manifest.write_text(content, encoding="utf-8")
            with self.assertRaises(TranscriptionError):
                self.run_m1()
        self.backend.recognize.assert_not_called()

    def test_existing_output_and_input_never_overwritten(self):
        self.run_m1()
        before = self.output.read_bytes()
        with self.assertRaises(FileExistsError):
            self.run_m1()
        self.assertEqual(self.output.read_bytes(), before)
        for target in (self.source, self.manifest):
            with self.assertRaises(FileExistsError):
                transcribe(self.manifest, target, backend=self.backend)

    def test_backend_failure_cleans_temporary_audio(self):
        self.backend.recognize.side_effect = TranscriptionError("ASR failed")
        with self.assertRaisesRegex(TranscriptionError, "ASR failed"):
            self.run_m1()
        self.assertFalse(self.analysis_path.exists())
        self.assertFalse(self.output.exists())

    def test_relative_source_path_rejected(self):
        self.data["source"]["path"] = "source.mov"
        save_manifest(self.manifest, self.data)
        with self.assertRaisesRegex(TranscriptionError, "absolute"):
            self.run_m1()

    def test_duplicate_stream_index_rejected(self):
        self.data["source"]["audio"][0]["stream_index"] = 0
        save_manifest(self.manifest, self.data)
        with self.assertRaisesRegex(TranscriptionError, "unique"):
            self.run_m1()
