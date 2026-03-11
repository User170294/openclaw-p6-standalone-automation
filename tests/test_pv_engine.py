import sys
import unittest
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CORE = ROOT / 'projects' / 'P6-Standalone-Automation' / 'scripts' / 'core'
if str(CORE) not in sys.path:
    sys.path.insert(0, str(CORE))

from pv_engine import spread_lv, week_label


class TestPvEngine(unittest.TestCase):
    def test_spread_lv_buckets_by_monday(self):
        bucket = {}
        spread_lv(date(2026, 2, 16), date(2026, 2, 20), 100.0, bucket)
        self.assertEqual(len(bucket), 1)
        mon = date(2026, 2, 16)
        self.assertAlmostEqual(bucket[mon], 100.0)

    def test_week_label_anchor(self):
        self.assertEqual(week_label(date(2026, 2, 16)), 'W08')
        self.assertEqual(week_label(date(2026, 2, 23)), 'W09')


if __name__ == '__main__':
    unittest.main()