import sys
import unittest
from datetime import date
from pathlib import Path
from tempfile import TemporaryDirectory

ROOT = Path(__file__).resolve().parents[1]
CORE = ROOT / 'projects' / 'P6-Standalone-Automation' / 'scripts' / 'core'
if str(CORE) not in sys.path:
    sys.path.insert(0, str(CORE))

from pv_engine import compute, load, spread_lv, week_label


class Args:
    def __init__(self, **kwargs):
        self.base_xer = kwargs.get('base_xer')
        self.upd_xer = kwargs.get('upd_xer')
        self.db = kwargs.get('db')
        self.proj_id = kwargs.get('proj_id')
        self.cutoff = kwargs.get('cutoff', '2026-02-22')
        self.mode = kwargs.get('mode', 'logic')
        self.out_dir = kwargs.get('out_dir', 'tmp')
        self.format = kwargs.get('format', 'json')


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

    def test_logic_uses_taskrsrc_rt_labor_for_pv_bac(self):
        xer = """%T\tTASKRSRC
%F\trsrc_type\ttarget_qty\ttarget_start_date\ttarget_end_date\tact_reg_qty\tact_ot_qty\tact_start_date\tact_end_date
%R\tRT_Labor\t100\t2026-02-16 08:00:00\t2026-02-20 18:00:00\t20\t0\t2026-02-16 08:00:00\t2026-02-17 18:00:00
%R\tRT_Mat\t999\t2026-02-16 08:00:00\t2026-02-20 18:00:00\t0\t0\t\t
"""
        with TemporaryDirectory() as tmp:
            base = Path(tmp) / 'base.xer'
            upd = Path(tmp) / 'upd.xer'
            base.write_text(xer, encoding='latin-1')
            upd.write_text(xer, encoding='latin-1')
            payload = load(Args(base_xer=str(base), upd_xer=str(upd), cutoff='2026-02-22', mode='logic'))
            result = compute(payload)
            pv_total = round(sum(r['pv_week'] for r in result['rows']), 4)
            self.assertEqual(pv_total, 100.0)
            self.assertEqual(result['bac'], 100.0)


if __name__ == '__main__':
    unittest.main()
