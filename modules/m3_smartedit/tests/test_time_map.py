import unittest
from modules.m3_smartedit.errors import SmartEditError
from modules.m3_smartedit.time_map import rebuild


class TimeMapTests(unittest.TestCase):
    def test_removal_splits_existing_source_mapping(self):
        base = [{"source": {"start_us": 0, "end_us": 1000}, "target": {"start_us": 0, "end_us": 1000}}]
        result, duration = rebuild(base, [(300, 600)])
        self.assertEqual(duration, 700)
        self.assertEqual([(x["source"]["start_us"], x["source"]["end_us"]) for x in result], [(0, 300), (600, 1000)])
        self.assertEqual(result[1]["target"], {"time_domain": "CUT", "start_us": 300, "end_us": 700})

    def test_never_reintroduces_speechcut_gap(self):
        base = [{"source": {"start_us": 0, "end_us": 100}}, {"source": {"start_us": 300, "end_us": 500}}]
        result, _ = rebuild(base, [(50, 350)])
        self.assertEqual([(x["source"]["start_us"], x["source"]["end_us"]) for x in result], [(0, 50), (350, 500)])

    def test_invalid_removal(self):
        with self.assertRaises(SmartEditError): rebuild([], [(10, 10)])
