"""Actual media boundaries and opt-in local ASR. No network access in these tests."""

import array
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
import wave

from core.time import seconds_to_us
from modules.m1_transcription import TranscriptionConfig, transcribe
from modules.m1_transcription.audio import extract_audio
from modules.m1_transcription.contracts import validate_contract


FFMPEG_AVAILABLE = bool(shutil.which("ffmpeg") and shutil.which("ffprobe"))


def run(command):
    return subprocess.run(command, capture_output=True, text=True, encoding="utf-8",
                          errors="replace", check=True, timeout=120)


def audio_stream(path):
    data = json.loads(run(["ffprobe", "-v", "error", "-show_streams", "-of", "json", str(path)]).stdout)
    stream = next(s for s in data["streams"] if s["codec_type"] == "audio")
    return {"stream_index": stream["index"], "start_us": seconds_to_us(stream["start_time"])}


@unittest.skipUnless(FFMPEG_AVAILABLE, "FFmpeg/FFprobe required for real-media tests")
class MediaIntegrationTests(unittest.TestCase):
    def test_delayed_track_keeps_source_origin(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "delayed.mov"
            run(["ffmpeg", "-v", "error", "-f", "lavfi", "-i", "color=s=160x90:r=25:d=3",
                 "-itsoffset", "0.5", "-f", "lavfi", "-i", "sine=frequency=440:sample_rate=16000:duration=2",
                 "-map", "0:v", "-map", "1:a", "-c:v", "mpeg4", "-c:a", "pcm_s16le", str(source)])
            stream = audio_stream(source)
            self.assertEqual(stream["start_us"], 500000)
            audio = extract_audio(source, stream, root / "analysis.wav", TranscriptionConfig())
            self.assertEqual(audio.origin_us, 500000)
            self.assertAlmostEqual(audio.duration_us, 2000000, delta=1000)

    def test_timestamp_gap_is_silence_not_removed(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "gap.mov"
            run(["ffmpeg", "-v", "error", "-f", "lavfi", "-i", "color=s=160x90:r=25:d=3",
                 "-f", "lavfi", "-i", "sine=frequency=440:sample_rate=16000:duration=3",
                 "-af", "aselect=not(between(t\\,0.5\\,1.5))",
                 "-c:v", "mpeg4", "-c:a", "aac", str(source)])
            packets = json.loads(run(["ffprobe", "-v", "error", "-select_streams", "a",
                                      "-show_packets", "-of", "json", str(source)]).stdout)["packets"]
            pts = [seconds_to_us(p["pts_time"]) for p in packets]
            self.assertTrue(any(b - a > 500000 for a, b in zip(pts, pts[1:])),
                            "Fixture must retain an actual timestamp gap")
            audio = extract_audio(source, audio_stream(source), root / "analysis.wav", TranscriptionConfig())
            with wave.open(str(audio.path), "rb") as wav:
                samples = array.array("h", wav.readframes(wav.getnframes()))
            # Check the middle of the gap, away from codec block boundaries.
            self.assertLess(max(abs(x) for x in samples[16000:20000]), 5)
            self.assertGreater(max(abs(x) for x in samples[32000:36000]), 100)
            self.assertAlmostEqual(audio.duration_us, 3000000, delta=1000)

    def test_aac_priming_does_not_shift_or_shorten_analysis(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "aac.mp4"
            run(["ffmpeg", "-v", "error", "-f", "lavfi", "-i", "color=s=160x90:r=25:d=2",
                 "-f", "lavfi", "-i", "sine=frequency=440:sample_rate=48000:duration=2",
                 "-c:v", "mpeg4", "-c:a", "aac", "-shortest", str(source)])
            audio = extract_audio(source, audio_stream(source), root / "analysis.wav", TranscriptionConfig())
            self.assertEqual(audio.origin_us, 0)
            self.assertAlmostEqual(audio.duration_us, 2000000, delta=25000)


@unittest.skipUnless(FFMPEG_AVAILABLE and os.name == "nt" and os.environ.get("AUTOREEL_TEST_MODEL"),
                     "Set AUTOREEL_TEST_MODEL to a cached local model to run Windows speech ASR")
class RealASRTests(unittest.TestCase):
    def test_speech_through_public_m0_m1_cli_offline(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            speech = root / "speech.wav"
            script = (
                "Add-Type -AssemblyName System.Speech; "
                "$s = New-Object System.Speech.Synthesis.SpeechSynthesizer; "
                "$s.SetOutputToWaveFile('" + str(speech).replace("'", "''") + "'); "
                "$s.Speak('Hello. This is a test of automatic video transcription. "
                "The original video stays unchanged.'); $s.Dispose()"
            )
            run(["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", script])
            source = root / "speech.mov"
            run(["ffmpeg", "-v", "error", "-f", "lavfi", "-i", "color=s=160x90:r=25:d=30",
                 "-i", str(speech), "-af", "apad=pad_dur=1", "-c:v", "mpeg4", "-c:a",
                 "pcm_s16le", "-shortest", str(source)])
            manifest = root / "source.json"
            output = root / "transcript.json"
            run([sys.executable, "-m", "modules.m0_ingest", str(source), str(manifest)])
            result = run([sys.executable, "-m", "modules.m1_transcription", str(manifest),
                          str(output), "--model", os.environ["AUTOREEL_TEST_MODEL"],
                          "--language", "en", "--device", "cpu"])
            transcript = json.loads(output.read_text(encoding="utf-8"))
            validate_contract(transcript, "transcript-1.0.0.json")
            self.assertEqual(transcript["status"], "transcribed", result.stderr)
            self.assertIn("video", transcript["text"].lower())
            self.assertGreaterEqual(sum(len(s["words"]) for s in transcript["segments"]), 5)
            self.assertEqual(transcript["engine"]["device"], "cpu")
            self.assertEqual(transcript["time_domain"], "SOURCE")

    def test_silent_audio_has_explicit_empty_transcription(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "silence.mp4"
            run(["ffmpeg", "-v", "error", "-f", "lavfi", "-i", "color=s=160x90:r=25:d=2",
                 "-f", "lavfi", "-i", "anullsrc=r=16000:cl=mono:d=2", "-c:v", "mpeg4",
                 "-c:a", "aac", "-shortest", str(source)])
            manifest = root / "source.json"
            run([sys.executable, "-m", "modules.m0_ingest", str(source), str(manifest)])
            result = transcribe(manifest, root / "transcript.json", TranscriptionConfig(
                model=os.environ["AUTOREEL_TEST_MODEL"], language="en"))
            self.assertEqual(result["status"], "no_speech_recognized")
            self.assertEqual(result["segments"], [])
