"""Unit tests for scripts/grocery.py.

Run: python -m unittest discover -s tests
"""

import sys
import unittest
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from grocery import fmt_qty, week_sunday  # noqa: E402


class FmtQtyTests(unittest.TestCase):
    def test_whole_number_drops_decimal(self):
        self.assertEqual(fmt_qty(2.0, "cup"), "2 cup")

    def test_fraction_keeps_decimal(self):
        self.assertEqual(fmt_qty(2.5, "cup"), "2.5 cup")

    def test_none_quantity_is_blank(self):
        self.assertEqual(fmt_qty(None, "cup"), "")

    def test_count_unit_omits_unit_label(self):
        self.assertEqual(fmt_qty(3, "count"), "3")

    def test_none_unit_omits_unit_label(self):
        self.assertEqual(fmt_qty(2, None), "2")

    def test_rounds_to_two_decimals(self):
        self.assertEqual(fmt_qty(1.333, "tbsp"), "1.33 tbsp")


class WeekSundayTests(unittest.TestCase):
    def test_explicit_date_is_returned_as_is(self):
        self.assertEqual(week_sunday("2026-08-16"), date(2026, 8, 16))

    def test_default_resolves_to_a_sunday(self):
        self.assertEqual(week_sunday().weekday(), 6)


if __name__ == "__main__":
    unittest.main()
