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

    def test_week_label_before_anchor(self):
        # Semanas anteriores al ancla deben generar W## consistente
        self.assertEqual(week_label(date(2026, 2, 9)), 'W07')
        self.assertEqual(week_label(date(2026, 2, 2)), 'W06')
        self.assertEqual(week_label(date(2026, 1, 26)), 'W05')

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

    def test_load_reads_base_taskrsrc_rows_from_db_when_proj_id_present(self):
        with TemporaryDirectory() as tmp:
            db = Path(tmp) / 'p6.db'
            import sqlite3
            con = sqlite3.connect(db)
            cur = con.cursor()
            cur.execute(
                'CREATE TABLE TASKRSRC (PROJ_ID INTEGER, TASK_ID INTEGER, RSRC_TYPE TEXT, TARGET_QTY REAL, TARGET_START_DATE TEXT, TARGET_END_DATE TEXT)'
            )
            cur.execute(
                'CREATE TABLE TASK (PROJ_ID INTEGER, TASK_ID INTEGER, CLNDR_ID INTEGER)'
            )
            cur.execute(
                'CREATE TABLE CALENDAR (CLNDR_ID INTEGER, CLNDR_DATA TEXT)'
            )
            cur.execute("INSERT INTO TASKRSRC VALUES (26432, 1, 'RT_Labor', 100, '2026-02-16 08:00:00', '2026-02-20 18:00:00')")
            cur.execute("INSERT INTO TASKRSRC VALUES (26432, 2, 'RT_Mat', 999, '2026-02-16 08:00:00', '2026-02-20 18:00:00')")
            cur.execute("INSERT INTO TASKRSRC VALUES (99999, 3, 'RT_Labor', 50, '2026-02-16 08:00:00', '2026-02-20 18:00:00')")
            con.commit()
            con.close()

            payload = load(Args(db=str(db), proj_id=26432, cutoff='2026-02-22', mode='logic'))
            self.assertEqual(len(payload['base_taskrsrc_rows']), 1)
            self.assertIn('rsrc_type', payload['base_taskrsrc_rows'][0])
            self.assertIn('target_qty', payload['base_taskrsrc_rows'][0])
            self.assertEqual(payload['base_taskrsrc_rows'][0]['rsrc_type'], 'RT_Labor')
            self.assertEqual(float(payload['base_taskrsrc_rows'][0]['target_qty']), 100.0)


    def test_remaining_uses_early_start_end_dates(self):
        """
        Early Remaining debe distribuirse usando early_start_date → early_end_date
        del registro TASK, no desde cutoff hacia adelante sin restricción.
        """
        with TemporaryDirectory() as tmp:
            db = Path(tmp) / 'p6.db'
            import sqlite3
            con = sqlite3.connect(db)
            cur = con.cursor()
            cur.execute('''
                CREATE TABLE TASK (
                    PROJ_ID INTEGER, TASK_ID INTEGER, TASK_CODE TEXT,
                    CLNDR_ID INTEGER, TASK_TYPE TEXT,
                    TARGET_START_DATE TEXT, TARGET_END_DATE TEXT,
                    ACT_START_DATE TEXT, ACT_END_DATE TEXT,
                    EARLY_START_DATE TEXT, EARLY_END_DATE TEXT,
                    TARGET_WORK_QTY REAL, ACT_WORK_QTY REAL, REMAIN_WORK_QTY REAL
                )
            ''')
            cur.execute('CREATE TABLE TASKRSRC (PROJ_ID INTEGER, TASK_ID INTEGER, RSRC_TYPE TEXT, TARGET_QTY REAL, TARGET_START_DATE TEXT, TARGET_END_DATE TEXT)')
            cur.execute('CREATE TABLE CALENDAR (CLNDR_ID INTEGER, CLNDR_DATA TEXT)')
            cur.execute("""
                INSERT INTO TASK VALUES (
                    26432, 1, 'A-001', NULL, 'TT_Task',
                    '2026-02-16 08:00:00', '2026-02-27 18:00:00',
                    '2026-02-16 08:00:00', NULL,
                    '2026-02-23 08:00:00', '2026-02-27 18:00:00',
                    100, 20, 80
                )
            """)
            con.commit()
            con.close()

            payload = load(Args(db=str(db), proj_id=26432, cutoff='2026-02-22', mode='logic'))
            result = compute(payload)

            re_total = round(sum(r.get('re_week', 0) for r in result['rows']), 4)
            self.assertAlmostEqual(re_total, 80.0, places=2)

            re_in_w09 = next((r.get('re_week', 0) for r in result['rows'] if r['week'] == 'W09'), 0)
            self.assertGreater(re_in_w09, 0)


if __name__ == '__main__':
    unittest.main()
