import copy
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from jsonschema import Draft202012Validator
from modules.m0_ingest import IngestConfig, IngestError, ingest
from modules.m0_ingest.metadata import normalize
from modules.m0_ingest.probe import probe_media

ROOT = Path(__file__).resolve().parents[3]
SCHEMA = json.loads((ROOT / "core/schemas/source-manifest-1.0.0.json").read_text(encoding="utf-8-sig"))


def fixture():
    return {
        "format": {"format_name": "mov,mp4,m4a,3gp,3g2,mj2", "duration": "3.5"},
        "streams": [
            {"index": 0, "codec_type": "video", "codec_name": "hevc",
             "width": 1920, "height": 1080, "time_base": "1/90000",
             "start_pts": 9000, "duration_ts": 270000,
             "avg_frame_rate": "30000/1001", "r_frame_rate": "30000/1001",
             "pix_fmt": "yuv420p10le", "color_transfer": "arib-std-b67",
             "color_primaries": "bt2020", "color_space": "bt2020nc",
             "side_data_list": [{"rotation": -90}]},
            {"index": 1, "codec_type": "audio", "codec_name": "aac",
             "sample_rate": "48000", "channels": 2, "start_time": "0.08",
             "duration": "3.02"}]}


class IngestTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / "vidéo exemple.MOV"
        self.source.write_bytes(b"fake source bytes")
        self.out = self.root / "project" / "source.json"

    def run_ingest(self, data=None):
        with patch("modules.m0_ingest.ingest.probe_media", return_value=data or fixture()):
            return ingest(self.source, self.out)

    def test_manifest_matches_schema_and_source_unchanged(self):
        before = self.source.read_bytes()
        result = self.run_ingest()
        Draft202012Validator.check_schema(SCHEMA)
        Draft202012Validator(SCHEMA).validate(result)
        self.assertEqual(json.loads(self.out.read_text(encoding="utf-8")), result)
        self.assertEqual(self.source.read_bytes(), before)
        self.assertEqual(result["source"]["sha256"], hashlib.sha256(before).hexdigest())
        self.assertEqual(result["source"]["path"], str(self.source.resolve()))
        self.assertEqual(result["source"]["duration_us"], 3000000)
        self.assertEqual(result["source"]["start_us"], 100000)
        self.assertEqual(result["source"]["audio"][0]["start_us"], 80000)
        self.assertEqual(result["source"]["video"]["display_width"], 1080)
        self.assertEqual(result["source"]["video"]["dynamic_range"], "HLG")

    def test_never_overwrite(self):
        self.run_ingest()
        previous = self.out.read_bytes()
        with self.assertRaises(FileExistsError):
            self.run_ingest()
        self.assertEqual(self.out.read_bytes(), previous)
        with self.assertRaises(FileExistsError):
            ingest(self.source, self.source)

    def test_missing_empty_wrong_extension(self):
        with self.assertRaises(FileNotFoundError):
            ingest(self.root / "absent.mp4", self.out)
        self.source.write_bytes(b"")
        with self.assertRaises(IngestError):
            self.run_ingest()
        other = self.root / "audio.wav"
        other.write_bytes(b"wav")
        with self.assertRaises(IngestError):
            ingest(other, self.out)
        self.assertFalse(self.out.exists())

    def test_source_change_detected(self):
        def changing_probe(*args):
            self.source.write_bytes(b"modified during probing")
            return fixture()
        with patch("modules.m0_ingest.ingest.probe_media", side_effect=changing_probe):
            with self.assertRaisesRegex(IngestError, "changed"):
                ingest(self.source, self.out)
        self.assertFalse(self.out.exists())

    def test_invalid_metadata_does_not_write(self):
        for change in ["no_video", "duration", "width", "rotation", "container"]:
            data = fixture()
            if change == "no_video":
                data["streams"] = []
            elif change == "duration":
                data["streams"][0]["duration_ts"] = -1
            elif change == "width":
                data["streams"][0]["width"] = 0
            elif change == "rotation":
                data["streams"][0]["side_data_list"] = [{"rotation": 45}]
            else:
                data["format"]["format_name"] = "matroska"
            with self.subTest(change=change), self.assertRaises(IngestError):
                self.run_ingest(data)
            self.assertFalse(self.out.exists())

    def test_no_audio_and_container_estimate_are_explicit(self):
        data = fixture()
        data["streams"] = data["streams"][:1]
        del data["streams"][0]["duration_ts"]
        result = self.run_ingest(data)
        Draft202012Validator(SCHEMA).validate(result)
        self.assertIn("NO_AUDIO_STREAM", result["warnings"])
        self.assertIn("VIDEO_DURATION_ESTIMATED_FROM_CONTAINER", result["warnings"])

    def test_primary_selection_excludes_cover_art(self):
        data = fixture()
        cover = copy.deepcopy(data["streams"][0])
        cover["index"] = 2
        cover["disposition"] = {"attached_pic": 1, "default": 1}
        primary = copy.deepcopy(data["streams"][0])
        primary["index"] = 3
        primary["disposition"] = {"default": 1}
        data["streams"] = [cover, *data["streams"], primary]
        result = self.run_ingest(data)
        self.assertEqual(result["source"]["video"]["stream_index"], 3)
        self.assertIn("MULTIPLE_VIDEO_STREAMS_PRIMARY_SELECTED", result["warnings"])

    def test_rates_do_not_assert_constant_frame_rate(self):
        data = fixture()
        data["streams"][0]["avg_frame_rate"] = "0/0"
        result = self.run_ingest(data)
        self.assertIsNone(result["source"]["video"]["avg_frame_rate"])
        self.assertEqual(result["source"]["video"]["frame_timing"], "UNDETERMINED")

    def test_sdr_and_pq(self):
        for transfer, expected in [("bt709", "SDR"), ("smpte2084", "PQ")]:
            data = fixture()
            data["streams"][0]["color_transfer"] = transfer
            self.assertEqual(normalize(data)[0]["video"]["dynamic_range"], expected)

    def test_config(self):
        for value in [0, -1, True, 1.5]:
            with self.assertRaises(ValueError):
                IngestConfig(timeout_s=value)


class ProbeTests(unittest.TestCase):
    def test_argument_list_no_shell_and_timeout(self):
        with patch("subprocess.run", return_value=subprocess.CompletedProcess([], 0, json.dumps(fixture()), "")) as run:
            probe_media(Path("C:/video with spaces.mp4"), "ffprobe.exe", 7)
        args, kwargs = run.call_args
        self.assertEqual(args[0][-1], str(Path("C:/video with spaces.mp4")))
        self.assertEqual(kwargs["timeout"], 7)
        self.assertNotIn("shell", kwargs)

    def test_process_and_json_failures(self):
        for result in [
            subprocess.CompletedProcess([], 1, "", "bad media"),
            subprocess.CompletedProcess([], 0, "not json", ""),
            subprocess.CompletedProcess([], 0, "[]", ""),
            subprocess.CompletedProcess([], 0, "{}", ""),
        ]:
            with patch("subprocess.run", return_value=result), self.assertRaises(IngestError):
                probe_media(Path("video.mp4"), "ffprobe", 1)
        for error in [FileNotFoundError("ffprobe"), subprocess.TimeoutExpired("ffprobe", 1)]:
            with patch("subprocess.run", side_effect=error), self.assertRaises(IngestError):
                probe_media(Path("video.mp4"), "ffprobe", 1)


class RealMediaTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"),
                         "FFmpeg/FFprobe unavailable: real-media integration not run")
    def test_generated_mp4_end_to_end(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "sample.mp4"
            subprocess.run(["ffmpeg", "-v", "error", "-f", "lavfi", "-i",
                            "color=c=black:s=160x90:r=25:d=1", "-f", "lavfi", "-i",
                            "sine=frequency=440:duration=1", "-c:v", "mpeg4",
                            "-c:a", "aac", "-shortest", str(source)], check=True, timeout=30)
            result = ingest(source, Path(directory) / "manifest.json")
            Draft202012Validator(SCHEMA).validate(result)
            self.assertEqual(result["source"]["duration_us"], 1000000)
            self.assertEqual(len(result["source"]["audio"]), 1)


class PublicationTests(unittest.TestCase):
    def test_failed_publication_cleans_staging_file(self):
        from modules.m0_ingest.manifest import publish_manifest
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "manifest.json"
            with patch("modules.m0_ingest.manifest.os.link", side_effect=OSError("disk error")):
                with self.assertRaises(OSError):
                    publish_manifest(target, "{}")
            self.assertEqual(list(Path(directory).iterdir()), [])

    def test_concurrent_destination_is_preserved(self):
        from modules.m0_ingest.manifest import publish_manifest
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "manifest.json"
            target.write_text("existing", encoding="utf-8")
            with self.assertRaises(FileExistsError):
                publish_manifest(target, "{}")
            self.assertEqual(target.read_text(encoding="utf-8"), "existing")
            self.assertEqual(list(Path(directory).iterdir()), [target])


class CliTests(unittest.TestCase):
    def test_error_is_actionable_without_traceback(self):
        result = subprocess.run([os.sys.executable, "-m", "modules.m0_ingest",
                                 "missing.mp4", "unused.json"],
                                capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 1)
        self.assertIn("M0:", result.stderr)
        self.assertNotIn("Traceback", result.stderr)

