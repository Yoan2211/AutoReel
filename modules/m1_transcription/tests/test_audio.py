from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch
import wave

from modules.m1_transcription.audio import extract_audio
from modules.m1_transcription import TranscriptionConfig, TranscriptionError


class AudioTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.output = Path(self.tmp.name) / "audio.wav"
        self.stream = {"stream_index": 3, "start_us": -250000}

    def test_command_retains_source_offsets_without_shell(self):
        with wave.open(str(self.output), "wb") as audio:
            audio.setparams((1, 2, 16000, 0, "NONE", "not compressed"))
            audio.writeframes(b"\0\0" * 16000)
        with patch("subprocess.run", return_value=subprocess.CompletedProcess([], 0, "", "")) as run:
            result = extract_audio(Path("source with spaces.mov"), self.stream, self.output,
                                   TranscriptionConfig(decode_timeout_s=7))
        command = run.call_args.args[0]
        self.assertIn("-copyts", command)
        self.assertEqual(command[command.index("-map") + 1], "0:3")
        self.assertIn("(-0.250000)", command[command.index("-af") + 1])
        self.assertIn("first_pts=0", command[command.index("-af") + 1])
        self.assertNotIn("shell", run.call_args.kwargs)
        self.assertEqual(run.call_args.kwargs["timeout"], 7)
        self.assertEqual(result.origin_us, -250000)
        self.assertEqual(result.duration_us, 1000000)

    def test_decode_errors(self):
        for failure in [FileNotFoundError("ffmpeg"), subprocess.TimeoutExpired("ffmpeg", 1)]:
            with patch("subprocess.run", side_effect=failure), self.assertRaises(TranscriptionError):
                extract_audio(Path("source.mov"), self.stream, self.output, TranscriptionConfig())
        with patch("subprocess.run", return_value=subprocess.CompletedProcess([], 1, "", "bad media")):
            with self.assertRaisesRegex(TranscriptionError, "bad media"):
                extract_audio(Path("source.mov"), self.stream, self.output, TranscriptionConfig())

    def test_empty_or_invalid_wav(self):
        for raw in [b"", b"invalid"]:
            self.output.write_bytes(raw)
            with patch("subprocess.run", return_value=subprocess.CompletedProcess([], 0, "", "")):
                with self.assertRaises(TranscriptionError):
                    extract_audio(Path("source.mov"), self.stream, self.output, TranscriptionConfig())


class DigitalSilenceTests(unittest.TestCase):
    def test_only_exact_zero_is_silence(self):
        from modules.m1_transcription.audio import is_digital_silence
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "audio.wav"
            for pcm, expected in [(b"\0\0" * 16000, True),
                                  (b"\0\0" * 15999 + b"\1\0", False), (b"", False)]:
                with wave.open(str(path), "wb") as audio:
                    audio.setparams((1, 2, 16000, 0, "NONE", "not compressed"))
                    audio.writeframes(pcm)
                self.assertEqual(is_digital_silence(path), expected)
