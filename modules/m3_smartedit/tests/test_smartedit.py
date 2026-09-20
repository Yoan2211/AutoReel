import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from modules.m3_smartedit import SmartEditConfig, SmartEditError, smartedit
from modules.m3_smartedit.contracts import validate
from modules.m3_smartedit.tests.fixtures import make_inputs


class SmartEditTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.inputs = make_inputs(self.root, ["Pourquoi le montage change tout ?", "Aujourd'hui je vais expliquer la méthode.", "La méthode rend le montage rapide.", "En conclusion abonne-toi."])
        self.plan, self.output_map = self.root/"out"/"edit_plan.json", self.root/"out"/"time_map.json"

    def run_m3(self, config=None): return smartedit(*self.inputs[:3], self.plan, self.output_map, config)

    def test_contracts_roles_hashes_and_default_identity_map(self):
        plan, time_map = self.run_m3()
        validate(plan, "edit-plan-1.0.0.json"); validate(time_map, "time-map-smartedit-1.0.0.json")
        self.assertEqual({x["role"] for x in plan["roles"]}, {"HOOK", "INTRODUCTION", "CONCLUSION", "CTA"})
        self.assertEqual(time_map["output_duration_us"], json.loads(self.inputs[2].read_text())["output_duration_us"])
        self.assertEqual(time_map["source"]["edit_plan_sha256"], hashlib.sha256(self.plan.read_bytes()).hexdigest())
        self.assertTrue(all("source_start_us" in p and "source_end_us" in p for p in plan["passages"]))

    def test_opt_in_duplicate_removal_recalculates_map(self):
        self.inputs = make_inputs(self.root, ["Une phrase identique.", "Une phrase identique."])
        plan, time_map = self.run_m3(SmartEditConfig(auto_remove_exact_duplicates=True))
        decision = next(x for x in plan["decisions"] if x["kind"] == "EXACT_DUPLICATE")
        self.assertEqual(decision["disposition"], "AUTO_REMOVE")
        self.assertLess(time_map["output_duration_us"], json.loads(self.inputs[2].read_text())["output_duration_us"])
        removed_start, removed_end = decision["source_start_us"], decision["source_end_us"]
        self.assertFalse(any(x["source"]["start_us"] < removed_end and removed_start < x["source"]["end_us"] for x in time_map["mappings"]))

    def test_hash_mismatch_rejected(self):
        cuts = json.loads(self.inputs[1].read_text()); cuts["source"]["transcript_sha256"] = "f"*64
        self.inputs[1].write_text(json.dumps(cuts), encoding="utf-8")
        with self.assertRaisesRegex(SmartEditError, "transcript"): self.run_m3()
        self.assertFalse(self.plan.exists())

    def test_words_removed_by_speechcut_are_not_semantically_analyzed(self):
        transcript = json.loads(self.inputs[0].read_text(encoding="utf-8"))
        first_end = transcript["segments"][0]["end_us"]
        speech_map = json.loads(self.inputs[2].read_text(encoding="utf-8"))
        speech_map["mappings"] = [{
            "id": "map000000",
            "source": {"time_domain": "SOURCE", "start_us": first_end + 1,
                       "end_us": speech_map["source_end_us"]},
            "target": {"time_domain": "CUT", "start_us": 0,
                       "end_us": speech_map["source_end_us"] - first_end - 1},
        }]
        speech_map["output_duration_us"] = speech_map["source_end_us"] - first_end - 1
        self.inputs[2].write_text(json.dumps(speech_map), encoding="utf-8")
        plan, _ = self.run_m3()
        self.assertNotIn("Pourquoi le montage change tout ?",
                         [item["text"] for item in plan["passages"]])
        hook_id = next(item["passage_id"] for item in plan["roles"] if item["role"] == "HOOK")
        hook = next(item for item in plan["passages"] if item["id"] == hook_id)
        self.assertIn("Aujourd'hui", hook["text"])

    def test_outputs_are_exclusive_and_rollback(self):
        self.plan.parent.mkdir(); self.plan.write_text("existing", encoding="utf-8")
        with self.assertRaises(FileExistsError): self.run_m3()
        self.assertEqual(self.plan.read_text(), "existing")
        self.plan.unlink()
        with patch("modules.m3_smartedit.output.os.fsync", side_effect=[None, OSError("disk")]):
            with self.assertRaises(OSError): self.run_m3()
        self.assertFalse(self.plan.exists()); self.assertFalse(self.output_map.exists())

    def test_paths_must_differ(self):
        with self.assertRaises(FileExistsError): smartedit(*self.inputs[:3], self.inputs[0], self.output_map)


class CliTests(unittest.TestCase):
    def test_clean_missing_input_error(self):
        result = subprocess.run([sys.executable, "-m", "modules.m3_smartedit", "a", "b", "c", "d", "e"], capture_output=True, text=True)
        self.assertEqual(result.returncode, 1); self.assertIn("M3:", result.stderr); self.assertNotIn("Traceback", result.stderr)
