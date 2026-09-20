import unittest

from modules.m2_speechcut.model import Candidate
from modules.m2_speechcut.resolve import select_auto
from modules.m2_speechcut.time_map import build_time_map


def candidate(kind, start, end, disposition="AUTO"):
    return Candidate(kind, start, end, disposition, "HIGH", "test")


class TimeMapTests(unittest.TestCase):
    def test_map_preserves_source_and_compacts_cut_domain(self):
        mappings, duration = build_time_map(-500_000, 3_000_000, [
            candidate("FILLER", 0, 200_000), candidate("LONG_SILENCE", 1_000_000, 2_000_000)])
        self.assertEqual(duration, 2_300_000)
        self.assertEqual(mappings[0]["source"],
                         {"time_domain": "SOURCE", "start_us": -500_000, "end_us": 0})
        self.assertEqual(mappings[-1]["target"],
                         {"time_domain": "CUT", "start_us": 1_300_000, "end_us": 2_300_000})

    def test_empty_map_for_fully_removed_source(self):
        mappings, duration = build_time_map(0, 100, [candidate("FILLER", 0, 100)])
        self.assertEqual((mappings, duration), ([], 0))

    def test_overlap_resolution_is_deterministic(self):
        candidates = [candidate("LONG_SILENCE", 0, 500), candidate("FILLER", 100, 200),
                      candidate("IMMEDIATE_REPETITION", 150, 300),
                      candidate("FILLER", 600, 700, "REVIEW")]
        selected, suppressed = select_auto(candidates)
        self.assertEqual([(item.kind, item.start_us) for item in selected],
                         [("IMMEDIATE_REPETITION", 150)])
        self.assertEqual(suppressed, {0, 1})

    def test_adjacent_removals_are_valid(self):
        mappings, duration = build_time_map(0, 1000, [
            candidate("FILLER", 100, 200), candidate("FILLER", 200, 300)])
        self.assertEqual(duration, 800)
        self.assertEqual(len(mappings), 2)
