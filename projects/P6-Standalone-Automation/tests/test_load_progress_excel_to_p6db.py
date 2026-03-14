from __future__ import annotations

import sqlite3
import sys
from datetime import datetime
from pathlib import Path

from openpyxl import Workbook

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_CORE = ROOT / 'scripts' / 'core'
if str(SCRIPTS_CORE) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_CORE))

import load_progress_excel_to_p6db as loader  # noqa: E402


def _build_loader_db(path: Path) -> None:
    con = sqlite3.connect(path)
    try:
        cur = con.cursor()
        cur.execute(
            '''
            CREATE TABLE PROJECT (
                PROJ_ID INTEGER,
                DEF_COMPLETE_PCT_TYPE TEXT
            )
            '''
        )
        cur.execute(
            '''
            CREATE TABLE TASK (
                TASK_ID INTEGER,
                TASK_CODE TEXT,
                TASK_NAME TEXT,
                PROJ_ID INTEGER,
                STATUS_CODE TEXT,
                COMPLETE_PCT_TYPE TEXT,
                CLNDR_ID INTEGER,
                TARGET_START_DATE TEXT,
                TARGET_END_DATE TEXT,
                ACT_START_DATE TEXT,
                ACT_END_DATE TEXT,
                TARGET_WORK_QTY REAL,
                ACT_WORK_QTY REAL,
                REMAIN_WORK_QTY REAL,
                UPDATE_DATE TEXT,
                UPDATE_USER TEXT
            )
            '''
        )
        cur.execute(
            '''
            CREATE TABLE TASKRSRC (
                PROJ_ID INTEGER,
                TASK_ID INTEGER,
                RSRC_TYPE TEXT,
                TARGET_QTY REAL,
                ACT_REG_QTY REAL,
                REMAIN_QTY REAL,
                TARGET_COST REAL,
                ACT_REG_COST REAL,
                REMAIN_COST REAL,
                ACT_START_DATE TEXT,
                ACT_END_DATE TEXT,
                UPDATE_DATE TEXT,
                UPDATE_USER TEXT
            )
            '''
        )
        cur.execute('INSERT INTO PROJECT (PROJ_ID, DEF_COMPLETE_PCT_TYPE) VALUES (?, ?)', (26432, 'CP_Phys'))
        cur.execute(
            '''
            INSERT INTO TASK (
                TASK_ID, TASK_CODE, TASK_NAME, PROJ_ID, STATUS_CODE, COMPLETE_PCT_TYPE, CLNDR_ID,
                TARGET_START_DATE, TARGET_END_DATE, ACT_START_DATE, ACT_END_DATE,
                TARGET_WORK_QTY, ACT_WORK_QTY, REMAIN_WORK_QTY, UPDATE_DATE, UPDATE_USER
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''',
            (
                10, 'A1000', 'Actividad 1000', 26432, 'TK_NotStart', 'CP_Phys', 100,
                '2026-03-17 08:00:00', '2026-03-19 18:00:00', None, None,
                80.0, 0.0, 80.0, None, None,
            ),
        )
        cur.execute(
            '''
            INSERT INTO TASKRSRC (
                PROJ_ID, TASK_ID, RSRC_TYPE, TARGET_QTY, ACT_REG_QTY, REMAIN_QTY,
                TARGET_COST, ACT_REG_COST, REMAIN_COST, ACT_START_DATE, ACT_END_DATE, UPDATE_DATE, UPDATE_USER
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''',
            (26432, 10, 'RT_Labor', 80.0, 0.0, 80.0, 800.0, 0.0, 800.0, None, None, None, None),
        )
        con.commit()
    finally:
        con.close()


def _build_workbook(path: Path, pct_to_load: float) -> None:
    wb = Workbook()
    ws = wb.active
    ws.title = loader.DEFAULT_SHEET
    ws.append([
        loader.DEFAULT_HEADERS['task_code'],
        loader.DEFAULT_HEADERS['task_name'],
        loader.DEFAULT_HEADERS['status'],
        loader.DEFAULT_HEADERS['pct_type_sheet'],
        loader.DEFAULT_HEADERS['calendar_id_sheet'],
        loader.DEFAULT_HEADERS['pct_to_load'],
        loader.DEFAULT_HEADERS['actual_start'],
        loader.DEFAULT_HEADERS['actual_end_if_100'],
    ])
    ws.append(['A1000', 'Actividad 1000', 'Not Started', 'CP_Phys', '100', pct_to_load, None, None])
    wb.save(path)


def test_zero_pct_row_keeps_task_not_started(tmp_path):
    db_path = tmp_path / 'loader.db'
    xlsx_path = tmp_path / 'loader.xlsx'
    _build_loader_db(db_path)
    _build_workbook(xlsx_path, 0.0)

    out_dir = tmp_path / 'out'
    argv = [
        'load_progress_excel_to_p6db.py',
        '--db', str(db_path),
        '--xlsx', str(xlsx_path),
        '--proj-id', '26432',
        '--out-dir', str(out_dir),
        '--apply',
    ]

    old_argv = sys.argv
    try:
        sys.argv = argv
        loader.main()
    finally:
        sys.argv = old_argv

    con = sqlite3.connect(db_path)
    try:
        row = con.execute(
            'SELECT STATUS_CODE, ACT_START_DATE, ACT_END_DATE, ACT_WORK_QTY, REMAIN_WORK_QTY FROM TASK WHERE PROJ_ID=? AND TASK_ID=?',
            (26432, 10),
        ).fetchone()
        assert row == ('TK_NotStart', None, None, 0.0, 80.0)
    finally:
        con.close()
