"""Tests for pilot_audit.py — schedule audit checks."""
from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_CORE = ROOT / "scripts" / "core"
if str(SCRIPTS_CORE) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_CORE))

import pilot_audit


# ---------------------------------------------------------------------------
# DB fixture helpers
# ---------------------------------------------------------------------------

def _make_db(tmp_path: Path) -> Path:
    db_path = tmp_path / "test.db"
    con = sqlite3.connect(db_path)
    cur = con.cursor()
    cur.executescript("""
        CREATE TABLE PROJECT (
            PROJ_ID INTEGER PRIMARY KEY,
            PROJ_SHORT_NAME TEXT
        );
        CREATE TABLE TASK (
            TASK_ID INTEGER PRIMARY KEY,
            PROJ_ID INTEGER,
            TASK_CODE TEXT,
            TASK_NAME TEXT,
            STATUS_CODE TEXT,
            TASK_TYPE TEXT,
            TARGET_END_DATE TEXT,
            TARGET_WORK_QTY REAL DEFAULT 0,
            ACT_WORK_QTY REAL DEFAULT 0,
            REMAIN_WORK_QTY REAL DEFAULT 0
        );
        CREATE TABLE TASKPRED (
            TASKPRED_ID INTEGER PRIMARY KEY,
            TASK_ID INTEGER,
            PRED_TASK_ID INTEGER
        );
        CREATE TABLE TASKRSRC (
            TASKRSRC_ID INTEGER PRIMARY KEY,
            PROJ_ID INTEGER,
            TASK_ID INTEGER,
            RSRC_TYPE TEXT,
            TARGET_QTY REAL DEFAULT 0,
            ACT_REG_QTY REAL DEFAULT 0,
            REMAIN_QTY REAL DEFAULT 0,
            TARGET_COST REAL DEFAULT 0,
            ACT_REG_COST REAL DEFAULT 0,
            REMAIN_COST REAL DEFAULT 0
        );
        INSERT INTO PROJECT VALUES (1, 'TEST_PROJ');
    """)
    con.commit()
    con.close()
    return db_path


# ---------------------------------------------------------------------------
# fetch_rows helper
# ---------------------------------------------------------------------------

def test_fetch_rows_returns_dicts(tmp_path):
    db = _make_db(tmp_path)
    con = sqlite3.connect(db)
    con.row_factory = sqlite3.Row
    cur = con.cursor()
    rows = pilot_audit.fetch_rows(cur, "SELECT PROJ_ID FROM PROJECT WHERE PROJ_ID=?", [1])
    con.close()
    assert len(rows) == 1
    assert rows[0]["PROJ_ID"] == 1


# ---------------------------------------------------------------------------
# COMPLETE_ZERO_ACT_WORK
# ---------------------------------------------------------------------------

def test_detects_complete_task_with_zero_act_work(tmp_path):
    db = _make_db(tmp_path)
    con = sqlite3.connect(db)
    cur = con.cursor()
    # Actividad completa pero sin horas reales
    cur.execute("INSERT INTO TASK VALUES (1,1,'A001','Tarea Test','TK_Complete','TT_Task',NULL,100,0,0)")
    con.commit()
    con.close()

    con = sqlite3.connect(db)
    con.row_factory = sqlite3.Row
    cur = con.cursor()
    rows = pilot_audit.fetch_rows(cur,
        "SELECT TASK_ID FROM TASK WHERE STATUS_CODE='TK_Complete' AND COALESCE(ACT_WORK_QTY,0)=0",
        [])
    con.close()
    assert len(rows) == 1


def test_no_false_positive_active_task(tmp_path):
    db = _make_db(tmp_path)
    con = sqlite3.connect(db)
    cur = con.cursor()
    # Actividad activa con ACT_WORK_QTY=0 — no debe disparar alerta de completa
    cur.execute("INSERT INTO TASK VALUES (1,1,'A001','Tarea Activa','TK_Active','TT_Task',NULL,100,0,100)")
    con.commit()
    con.close()

    con = sqlite3.connect(db)
    con.row_factory = sqlite3.Row
    cur = con.cursor()
    rows = pilot_audit.fetch_rows(cur,
        "SELECT TASK_ID FROM TASK WHERE STATUS_CODE='TK_Complete' AND COALESCE(ACT_WORK_QTY,0)=0",
        [])
    con.close()
    assert len(rows) == 0


# ---------------------------------------------------------------------------
# TASK_WORK_MISMATCH check
# ---------------------------------------------------------------------------

def test_detects_task_taskrsrc_mismatch(tmp_path):
    db = _make_db(tmp_path)
    con = sqlite3.connect(db)
    cur = con.cursor()
    # TASK dice 100 HH pero TASKRSRC tiene 80 HH → mismatch
    cur.execute("INSERT INTO TASK VALUES (1,1,'A001','Tarea','TK_Active','TT_Task',NULL,100,50,50)")
    cur.execute("INSERT INTO TASKRSRC VALUES (1,1,1,'RT_Labor',80,40,40,0,0,0)")
    con.commit()
    con.close()

    con = sqlite3.connect(db)
    con.row_factory = sqlite3.Row
    cur = con.cursor()
    rows = pilot_audit.fetch_rows(cur, """
        SELECT t.TASK_ID,
            ROUND(COALESCE(t.TARGET_WORK_QTY,0),4) AS TW,
            ROUND(COALESCE(SUM(CASE WHEN tr.RSRC_TYPE='RT_Labor' THEN tr.TARGET_QTY ELSE 0 END),0),4) AS TR_TW
        FROM TASK t
        LEFT JOIN TASKRSRC tr ON tr.TASK_ID=t.TASK_ID
        GROUP BY t.TASK_ID, t.TARGET_WORK_QTY
        HAVING ABS(COALESCE(t.TARGET_WORK_QTY,0) - COALESCE(SUM(CASE WHEN tr.RSRC_TYPE='RT_Labor' THEN tr.TARGET_QTY ELSE 0 END),0)) > 0.01
    """, [])
    con.close()
    assert len(rows) == 1


def test_no_mismatch_when_values_match(tmp_path):
    db = _make_db(tmp_path)
    con = sqlite3.connect(db)
    cur = con.cursor()
    cur.execute("INSERT INTO TASK VALUES (1,1,'A001','Tarea','TK_Active','TT_Task',NULL,100,50,50)")
    cur.execute("INSERT INTO TASKRSRC VALUES (1,1,1,'RT_Labor',100,50,50,0,0,0)")
    con.commit()
    con.close()

    con = sqlite3.connect(db)
    con.row_factory = sqlite3.Row
    cur = con.cursor()
    rows = pilot_audit.fetch_rows(cur, """
        SELECT t.TASK_ID
        FROM TASK t
        LEFT JOIN TASKRSRC tr ON tr.TASK_ID=t.TASK_ID
        GROUP BY t.TASK_ID, t.TARGET_WORK_QTY
        HAVING ABS(COALESCE(t.TARGET_WORK_QTY,0) - COALESCE(SUM(CASE WHEN tr.RSRC_TYPE='RT_Labor' THEN tr.TARGET_QTY ELSE 0 END),0)) > 0.01
    """, [])
    con.close()
    assert len(rows) == 0
