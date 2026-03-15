from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / 'scripts'
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from p6_utils import clone_resource_payload, get_next_id, insert_row, open_db, set_next_id, split3  # noqa: E402


def test_split3_preserves_total():
    vals = split3(7740.0)
    assert len(vals) == 3
    assert round(sum(vals), 4) == 7740.0


def test_clone_resource_payload_clears_sensitive_fields(tmp_path):
    db = tmp_path / 'rsrc.db'
    con = sqlite3.connect(db)
    try:
        con.row_factory = sqlite3.Row
        cur = con.cursor()
        cur.execute(
            'CREATE TABLE RSRC (RSRC_ID INTEGER, RSRC_SHORT_NAME TEXT, RSRC_NAME TEXT, RSRC_TITLE_NAME TEXT, RSRC_TYPE TEXT, GUID TEXT, EMAIL_ADDR TEXT, ACTIVE_FLAG TEXT)'
        )
        cur.execute("INSERT INTO RSRC VALUES (1, 'OLD', 'Old Name', 'OLDTITLE', 'RT_Mat', 'abc', 'x@y.z', 'N')")
        con.commit()
        row = cur.execute('SELECT * FROM RSRC').fetchone()
        payload = clone_resource_payload(row, 10, 'OP1', 'Operador 1', title='CUADRILLA')
        assert payload['RSRC_ID'] == 10
        assert payload['RSRC_SHORT_NAME'] == 'OP1'
        assert payload['RSRC_NAME'] == 'Operador 1'
        assert payload['RSRC_TITLE_NAME'] == 'CUADRILLA'
        assert payload['RSRC_TYPE'] == 'RT_Labor'
        assert payload['GUID'] is None
        assert payload['EMAIL_ADDR'] is None
        assert payload['ACTIVE_FLAG'] == 'Y'
    finally:
        con.close()


def test_open_db_and_nextkey_roundtrip(tmp_path):
    db = tmp_path / 'test.db'
    con = sqlite3.connect(db)
    try:
        cur = con.cursor()
        cur.execute('CREATE TABLE NEXTKEY (KEY_NAME TEXT PRIMARY KEY, KEY_SEQ_NUM INTEGER, UPDATE_DATE TEXT, UPDATE_USER TEXT)')
        cur.execute("INSERT INTO NEXTKEY VALUES ('rsrc_rsrc_id', 42, '', '')")
        cur.execute('CREATE TABLE T (ID INTEGER PRIMARY KEY, VAL TEXT)')
        con.commit()
    finally:
        con.close()

    con2 = open_db(db)
    try:
        cur2 = con2.cursor()
        assert get_next_id(cur2, 'rsrc_rsrc_id') == 42
        set_next_id(cur2, 'rsrc_rsrc_id', 50)
        insert_row(cur2, 'T', {'ID': 1, 'VAL': 'ok'})
        con2.commit()
        assert get_next_id(cur2, 'rsrc_rsrc_id') == 50
        saved = cur2.execute('SELECT VAL FROM T WHERE ID=1').fetchone()[0]
        assert saved == 'ok'
    finally:
        con2.close()
