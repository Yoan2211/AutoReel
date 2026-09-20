import unittest

from core.time import seconds_to_timestamp_us, seconds_to_us, us_to_seconds_text


class M1TimeTests(unittest.TestCase):
    def test_exact_roundtrip(self):
        for value in [0, 1, -1, 123456789, -9000123456, 10**20]:
            self.assertEqual(seconds_to_us(us_to_seconds_text(value)), value)

    def test_relative_timestamp_uses_declared_origin(self):
        self.assertEqual(seconds_to_timestamp_us("0.0000005", -500000), -499999)
        self.assertEqual(seconds_to_timestamp_us("1.25", 500000), 1750000)

    def test_invalid_timestamp_types(self):
        for value in [True, 1.5, "100"]:
            with self.assertRaises(ValueError):
                us_to_seconds_text(value)
            with self.assertRaises(ValueError):
                seconds_to_timestamp_us("1", value)
