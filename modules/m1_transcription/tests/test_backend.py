from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
import wave
from unittest.mock import Mock, patch

from modules.m1_transcription import TranscriptionConfig, TranscriptionError
from modules.m1_transcription.faster_whisper_backend import FasterWhisperBackend


def engine_result():
    word = SimpleNamespace(start=0.1, end=0.5, word=" Hello", probability=0.9)
    segment = SimpleNamespace(start=0.1, end=0.5, text=" Hello",
                              no_speech_prob=0.01, words=[word])
    return iter([segment]), SimpleNamespace(language="en", language_probability=1.0)


class BackendTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.model_path = Path(self.tmp.name)
        self.wav_path = self.model_path / "analysis.wav"
        with wave.open(str(self.wav_path), "wb") as audio:
            audio.setparams((1, 2, 16000, 0, "NONE", "not compressed"))
            audio.writeframes(b"\x01\x00" * 16000)
        for name in ("model.bin", "config.json", "tokenizer.json"):
            (self.model_path / name).write_text("fixture", encoding="utf-8")
        self.model = Mock()
        self.model.transcribe.side_effect = lambda *a, **kw: engine_result()
        self.factory = Mock(return_value=self.model)
        self.download = Mock(return_value=str(self.model_path))
        self.modules = {
            "faster_whisper": SimpleNamespace(WhisperModel=self.factory),
            "faster_whisper.utils": SimpleNamespace(download_model=self.download),
            "ctranslate2": SimpleNamespace(get_cuda_device_count=lambda: 0),
        }

    def recognize(self, **options):
        with patch.dict("sys.modules", self.modules), patch(
            "modules.m1_transcription.faster_whisper_backend.version", return_value="test-version"
        ):
            return FasterWhisperBackend().recognize(self.wav_path, TranscriptionConfig(**options))

    def test_cpu_offline_word_timestamps_no_editing(self):
        result = self.recognize()
        self.assertEqual(result.device, "cpu")
        self.assertEqual(result.compute_type, "int8")
        self.assertEqual(result.segments[0].words[0].start_seconds, "0.1")
        self.assertTrue(self.download.call_args.kwargs["local_files_only"])
        options = self.model.transcribe.call_args.kwargs
        self.assertTrue(options["word_timestamps"])
        self.assertFalse(options["vad_filter"])
        self.assertFalse(options["condition_on_previous_text"])
        self.assertEqual(options["task"], "transcribe")

    def test_explicit_download_opt_in(self):
        self.recognize(allow_model_download=True)
        self.assertFalse(self.download.call_args.kwargs["local_files_only"])

    def test_local_model_never_downloaded(self):
        self.recognize(model=str(self.model_path))
        self.download.assert_not_called()

    def test_missing_tokenizer_rejected_before_engine_load(self):
        (self.model_path / "tokenizer.json").unlink()
        with self.assertRaisesRegex(TranscriptionError, "tokenizer"):
            self.recognize(model=str(self.model_path))
        self.factory.assert_not_called()

    def test_gpu_load_failure_falls_back(self):
        self.factory.side_effect = [RuntimeError("missing CUDA"), self.model]
        result = self.recognize(device="cuda")
        self.assertEqual(result.device, "cpu")
        self.assertEqual(result.warnings, ("CPU_FALLBACK",))
        self.assertEqual([c.kwargs["device"] for c in self.factory.call_args_list], ["cuda", "cpu"])

    def test_gpu_lazy_failure_falls_back(self):
        def lazy_failure():
            raise RuntimeError("CUDA OOM")
            yield  # Make failure happen during iteration.
        self.model.transcribe.side_effect = [
            (lazy_failure(), SimpleNamespace(language="en", language_probability=1.0)),
            engine_result(),
        ]
        result = self.recognize(device="cuda")
        self.assertIn("CPU_FALLBACK", result.warnings)

    def test_cpu_error_not_retried_and_fallback_can_be_disabled(self):
        self.factory.side_effect = RuntimeError("engine failure")
        for options in [{}, {"device": "cuda", "cpu_fallback": False}]:
            with self.assertRaisesRegex(TranscriptionError, "engine failure"):
                self.recognize(**options)
        self.assertEqual(self.factory.call_count, 2)

    def test_auto_without_gpu_uses_cpu(self):
        self.assertEqual(self.recognize(device="auto").device, "cpu")

    def test_unavailable_model_is_actionable(self):
        self.download.side_effect = OSError("not cached")
        with self.assertRaisesRegex(TranscriptionError, "allow_model_download"):
            self.recognize()

    def test_gpu_discovery_failure_falls_back(self):
        self.modules["ctranslate2"] = SimpleNamespace(
            get_cuda_device_count=Mock(side_effect=RuntimeError("driver unavailable")))
        result = self.recognize(device="auto")
        self.assertEqual(result.device, "cpu")
        self.assertIn("CPU_FALLBACK", result.warnings)
        with self.assertRaisesRegex(TranscriptionError, "discovery"):
            self.recognize(device="auto", cpu_fallback=False)

    def test_provider_validation_error_has_module_error_type(self):
        self.model.transcribe.side_effect = ValueError("unsupported language")
        with self.assertRaisesRegex(TranscriptionError, "Invalid ASR request"):
            self.recognize()

    def test_network_resolution_failure_has_actionable_error(self):
        self.download.side_effect = RuntimeError("network unavailable")
        with self.assertRaisesRegex(TranscriptionError, "Model unavailable"):
            self.recognize(allow_model_download=True)

    def test_digital_silence_bypasses_model_and_network(self):
        with wave.open(str(self.wav_path), "wb") as audio:
            audio.setparams((1, 2, 16000, 0, "NONE", "not compressed"))
            audio.writeframes(b"\0\0" * 16000)
        result = self.recognize()
        self.assertEqual(result.segments, ())
        self.assertEqual(result.language, "und")
        self.assertEqual(result.engine, "pcm-silence-check")
        self.download.assert_not_called()
        self.factory.assert_not_called()
