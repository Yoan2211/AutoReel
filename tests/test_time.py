import unittest
from core.time import TimeDomain, seconds_to_us, ticks_to_us


class TimeTests(unittest.TestCase):
    def test_decimal_rounding(self):
        for raw, expected in [("1.0000005", 1000001), ("-0.0000005", -1),
                              ("0", 0), ("3600.123456", 3600123456)]:
            self.assertEqual(seconds_to_us(raw), expected)

    def test_tick_rounding(self):
        self.assertEqual(ticks_to_us(1, "1/90000"), 11)
        self.assertEqual(ticks_to_us(1, "1/2000000"), 1)
        self.assertEqual(ticks_to_us(-1, "1/2000000"), -1)
        self.assertEqual(ticks_to_us(90000, "1/90000"), 1000000)

    def test_invalid_times(self):
        for value in [True, 0.1, "N/A", "NaN", "Infinity", None]:
            with self.subTest(value=value), self.assertRaises(ValueError):
                seconds_to_us(value)
        for base in ["0/1", "1/0", "-1/2", "bad"]:
            with self.subTest(base=base), self.assertRaises(ValueError):
                ticks_to_us(1, base)

    def test_domains_remain_distinct(self):
        self.assertEqual({d.value for d in TimeDomain}, {"SOURCE", "CUT", "TIMELINE"})

