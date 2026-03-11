from pathlib import Path
import sqlite3
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
P6_SCRIPTS = ROOT / 'projects' / 'P6-Standalone-Automation' / 'scripts'
if str(P6_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(P6_SCRIPTS))

from p6_utils import clone_resource_payload, get_next_id, insert_row, open_db, set_next_id, split3


class TestP6Utils(unittest.TestCase):
    def test_split3_preserves_total(self):
        vals = split3(7740.0)
        self.assertEqual(len(vals), 3)
        self.assertEqual(round(sum(vals), 4), 7740.0)

    def test_clone_resource_payload_clears_sensitive_fields(self):
        from tempfile import TemporaryDirectory

        with TemporaryDirectory() as tmp:
            db = Path(tmp) / 'rsrc.db'
            con = sqlite3.connect(db)
            con.row_factory = sqlite3.Row
            cur = con.cursor()
            cur.execute(
                'CREATE TABLE RSRC (RSRC_ID INTEGER, RSRC_SHORT_NAME TEXT, RSRC_NAME TEXT, RSRC_TITLE_NAME TEXT, RSRC_TYPE TEXT, GUID TEXT, EMAIL_ADDR TEXT, ACTIVE_FLAG TEXT)'
            )
            cur.execute("INSERT INTO RSRC VALUES (1, 'OLD', 'Old Name', 'OLDTITLE', 'RT_Mat', 'abc', 'x@y.z', 'N')")
            con.commit()
            row = cur.execute('SELECT * FROM RSRC').fetchone()
            payload = clone_resource_payload(row, 10, 'OP1', 'Operador 1', title='CUADRILLA')
            self.assertEqual(payload['RSRC_ID'], 10)
            self.assertEqual(payload['RSRC_SHORT_NAME'], 'OP1')
            self.assertEqual(payload['RSRC_NAME'], 'Operador 1')
            self.assertEqual(payload['RSRC_TITLE_NAME'], 'CUADRILLA')
            self.assertEqual(payload['RSRC_TYPE'], 'RT_Labor')
            self.assertIsNone(payload['GUID'])
            self.assertIsNone(payload['EMAIL_ADDR'])
            self.assertEqual(payload['ACTIVE_FLAG'], 'Y')
            con.close()

    def test_open_db_and_nextkey_roundtrip(self):
        from tempfile import TemporaryDirectory

        with TemporaryDirectory() as tmp:
            db = Path(tmp) / 'test.db'
            con = sqlite3.connect(db)
            cur = con.cursor()
            cur.execute('CREATE TABLE NEXTKEY (KEY_NAME TEXT PRIMARY KEY, KEY_SEQ_NUM INTEGER, UPDATE_DATE TEXT, UPDATE_USER TEXT)')
            cur.execute("INSERT INTO NEXTKEY VALUES ('rsrc_rsrc_id', 42, '', '')")
            cur.execute('CREATE TABLE T (ID INTEGER PRIMARY KEY, VAL TEXT)')
            con.commit()
            con.close()

            con2 = open_db(db)
            cur2 = con2.cursor()
            self.assertEqual(get_next_id(cur2, 'rsrc_rsrc_id'), 42)
            set_next_id(cur2, 'rsrc_rsrc_id', 50)
            insert_row(cur2, 'T', {'ID': 1, 'VAL': 'ok'})
            con2.commit()
            self.assertEqual(get_next_id(cur2, 'rsrc_rsrc_id'), 50)
            saved = cur2.execute('SELECT VAL FROM T WHERE ID=1').fetchone()[0]
            self.assertEqual(saved, 'ok')
            con2.close()


if __name__ == '__main__':
    unittest.main()
