from __future__ import annotations

import sqlite3
import sys
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_CORE = ROOT / 'scripts' / 'core'
if str(SCRIPTS_CORE) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_CORE))

import pv_engine  # noqa: E402


def _build_fake_db(path: Path) -> None:
    con = sqlite3.connect(path)
    try:
        cur = con.cursor()
        cur.execute(
            '''
            CREATE TABLE TASKRSRC (
                PROJ_ID INTEGER,
                RSRC_TYPE TEXT,
                TARGET_QTY REAL,
                TARGET_START_DATE TEXT,
                TARGET_END_DATE TEXT,
                ACT_REG_QTY REAL,
                ACT_OT_QTY REAL,
                ACT_START_DATE TEXT,
                ACT_END_DATE TEXT
            )
            '''
        )
        cur.executemany(
            '''
            INSERT INTO TASKRSRC (
                PROJ_ID, RSRC_TYPE, TARGET_QTY, TARGET_START_DATE, TARGET_END_DATE,
                ACT_REG_QTY, ACT_OT_QTY, ACT_START_DATE, ACT_END_DATE
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''',
            [
                (26432, 'RT_Labor', 80.0, '2026-02-16 08:00:00', '2026-02-20 17:00:00', 0.0, 0.0, None, None),
                (26432, 'RT_Mat', 999.0, '2026-02-16 08:00:00', '2026-02-20 17:00:00', 0.0, 0.0, None, None),
                (99999, 'RT_Labor', 500.0, '2026-02-16 08:00:00', '2026-02-20 17:00:00', 0.0, 0.0, None, None),
            ],
        )
        con.commit()
    finally:
        con.close()


def test_logic_uses_taskrsrc_rt_labor_for_pv_bac(tmp_path):
    db_path = tmp_path / 'pv_engine_fake.db'
    _build_fake_db(db_path)

    args = SimpleNamespace(
        mode='logic',
        cutoff='2026-02-20',
        base_xer=None,
        upd_xer=None,
        db=str(db_path),
        proj_id=26432,
    )

    payload = pv_engine.load(args)
    result = pv_engine.compute(payload)

    assert payload['base_source'] == 'db'
    assert len(payload['base_taskrsrc_rows']) == 1
    assert result['mode'] == 'logic'
    assert result['stub'] is False
    assert result['bac'] == 80.0
    assert result['rows'][0]['week'] == 'W08'
    assert result['rows'][0]['pv_week'] == 80.0
    assert 'DB SQLite primaria' in result['note']
