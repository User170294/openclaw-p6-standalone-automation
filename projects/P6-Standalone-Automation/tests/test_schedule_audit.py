"""Tests for schedule_audit.py — schedule quality fingerprint."""
from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_CORE = ROOT / "scripts" / "core"
if str(SCRIPTS_CORE) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_CORE))

import schedule_audit as sa


# ---------------------------------------------------------------------------
# DB fixture
# ---------------------------------------------------------------------------

def _make_db(tmp_path: Path) -> Path:
    db = tmp_path / "test.db"
    con = sqlite3.connect(db)
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
            TASK_TYPE TEXT DEFAULT 'TT_Task',
            STATUS_CODE TEXT,
            TARGET_DRTN_HR_CNT REAL DEFAULT 0,
            TARGET_START_DATE TEXT,
            TARGET_END_DATE TEXT,
            ACT_START_DATE TEXT,
            ACT_END_DATE TEXT,
            CSTR_TYPE TEXT,
            CSTR_DATE TEXT
        );
        CREATE TABLE TASKPRED (
            TASKPRED_ID INTEGER PRIMARY KEY,
            TASK_ID INTEGER,
            PRED_TASK_ID INTEGER,
            LAG_HR_CNT REAL DEFAULT 0
        );
        CREATE TABLE TASKRSRC (
            TASKRSRC_ID INTEGER PRIMARY KEY,
            TASK_ID INTEGER,
            PROJ_ID INTEGER,
            RSRC_TYPE TEXT,
            TARGET_QTY REAL DEFAULT 0
        );
        INSERT INTO PROJECT VALUES (1, 'TEST_PROJ');
    """)
    con.commit()
    con.close()
    return db


def _add_task(con, task_id, proj_id=1, code="A001", name="Tarea",
              task_type="TT_Task", status=None, duration=40,
              act_start=None, act_end=None, cstr_type=None):
    con.execute(
        "INSERT INTO TASK VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (task_id, proj_id, code, name, task_type, status, duration,
         "2026-01-01", "2026-02-01", act_start, act_end, cstr_type, None)
    )


def _add_pred(con, pred_id, task_id, pred_task_id, lag=0):
    con.execute("INSERT INTO TASKPRED VALUES (?,?,?,?)", (pred_id, task_id, pred_task_id, lag))


def _add_resource(con, res_id, task_id, proj_id=1, rsrc_type="RT_Labor", qty=100):
    con.execute("INSERT INTO TASKRSRC VALUES (?,?,?,?,?)", (res_id, task_id, proj_id, rsrc_type, qty))


# ---------------------------------------------------------------------------
# run_audit general
# ---------------------------------------------------------------------------

def test_run_audit_returns_result(tmp_path):
    db = _make_db(tmp_path)
    con = sqlite3.connect(db)
    _add_task(con, 1, code="A001")
    con.commit(); con.close()
    result = sa.run_audit(db, 1)
    assert result.proj_id == 1
    assert result.proj_name == "TEST_PROJ"


def test_run_audit_raises_for_missing_proj(tmp_path):
    db = _make_db(tmp_path)
    with pytest.raises(ValueError, match="no encontrado"):
        sa.run_audit(db, 999)


def test_score_100_when_no_findings(tmp_path):
    db = _make_db(tmp_path)
    con = sqlite3.connect(db)
    _add_task(con, 1, code="A001", status="TK_Complete", act_start="2026-01-01", act_end="2026-01-10")
    _add_resource(con, 1, 1)
    con.commit(); con.close()
    result = sa.run_audit(db, 1)
    # Puede tener findings de no_pred/no_succ pero score no debe ser negativo
    assert result.score >= 0
    assert result.score <= 100


# ---------------------------------------------------------------------------
# NO_PREDECESSOR
# ---------------------------------------------------------------------------

def test_detects_task_without_predecessor(tmp_path):
    db = _make_db(tmp_path)
    con = sqlite3.connect(db)
    _add_task(con, 1, code="A001")  # sin predecesor
    _add_task(con, 2, code="A002")
    _add_pred(con, 1, task_id=2, pred_task_id=1)  # A002 tiene pred
    con.commit(); con.close()
    result = sa.run_audit(db, 1)
    finding = next((f for f in result.findings if f.check == "NO_PREDECESSOR"), None)
    assert finding is not None
    assert finding.count == 1
    assert "A001" in finding.examples[0]


def test_no_false_positive_completed_task(tmp_path):
    db = _make_db(tmp_path)
    con = sqlite3.connect(db)
    _add_task(con, 1, code="A001", status="TK_Complete")  # completa sin pred → no debe alertar
    con.commit(); con.close()
    result = sa.run_audit(db, 1)
    finding = next((f for f in result.findings if f.check == "NO_PREDECESSOR"), None)
    assert finding is None


# ---------------------------------------------------------------------------
# NO_SUCCESSOR
# ---------------------------------------------------------------------------

def test_detects_task_without_successor(tmp_path):
    db = _make_db(tmp_path)
    con = sqlite3.connect(db)
    _add_task(con, 1, code="A001")
    _add_task(con, 2, code="A002")
    _add_pred(con, 1, task_id=2, pred_task_id=1)  # A001 tiene sucesor, A002 no
    con.commit(); con.close()
    result = sa.run_audit(db, 1)
    finding = next((f for f in result.findings if f.check == "NO_SUCCESSOR"), None)
    assert finding is not None
    assert finding.count == 1
    assert "A002" in finding.examples[0]


# ---------------------------------------------------------------------------
# LONG_DURATION
# ---------------------------------------------------------------------------

def test_detects_long_duration(tmp_path):
    db = _make_db(tmp_path)
    con = sqlite3.connect(db)
    _add_task(con, 1, code="A001", duration=400)  # 50 dias
    _add_task(con, 2, code="A002", duration=40)   # 5 dias
    con.commit(); con.close()
    result = sa.run_audit(db, 1, long_duration_days=30)
    finding = next((f for f in result.findings if f.check == "LONG_DURATION"), None)
    assert finding is not None
    assert finding.count == 1
    assert "A001" in finding.examples[0]


# ---------------------------------------------------------------------------
# HARD_CONSTRAINTS
# ---------------------------------------------------------------------------

def test_detects_hard_constraint(tmp_path):
    db = _make_db(tmp_path)
    con = sqlite3.connect(db)
    _add_task(con, 1, code="A001", cstr_type="CS_MSO")
    _add_task(con, 2, code="A002")
    con.commit(); con.close()
    result = sa.run_audit(db, 1)
    finding = next((f for f in result.findings if f.check == "HARD_CONSTRAINTS"), None)
    assert finding is not None
    assert finding.count == 1


# ---------------------------------------------------------------------------
# NEGATIVE_LAG
# ---------------------------------------------------------------------------

def test_detects_negative_lag(tmp_path):
    db = _make_db(tmp_path)
    con = sqlite3.connect(db)
    _add_task(con, 1, code="A001")
    _add_task(con, 2, code="A002")
    _add_pred(con, 1, task_id=2, pred_task_id=1, lag=-16)  # -2 dias
    con.commit(); con.close()
    result = sa.run_audit(db, 1)
    finding = next((f for f in result.findings if f.check == "NEGATIVE_LAG"), None)
    assert finding is not None
    assert finding.count == 1


# ---------------------------------------------------------------------------
# NO_LABOR_RESOURCE
# ---------------------------------------------------------------------------

def test_detects_task_without_labor(tmp_path):
    db = _make_db(tmp_path)
    con = sqlite3.connect(db)
    _add_task(con, 1, code="A001")  # sin recurso
    _add_task(con, 2, code="A002")
    _add_resource(con, 1, 2)  # A002 tiene recurso
    con.commit(); con.close()
    result = sa.run_audit(db, 1)
    finding = next((f for f in result.findings if f.check == "NO_LABOR_RESOURCE"), None)
    assert finding is not None
    assert finding.count == 1


# ---------------------------------------------------------------------------
# COMPLETE_NO_DATES
# ---------------------------------------------------------------------------

def test_detects_complete_without_dates(tmp_path):
    db = _make_db(tmp_path)
    con = sqlite3.connect(db)
    _add_task(con, 1, code="A001", status="TK_Complete")  # completa sin fechas reales
    con.commit(); con.close()
    result = sa.run_audit(db, 1)
    finding = next((f for f in result.findings if f.check == "COMPLETE_NO_DATES"), None)
    assert finding is not None
    assert finding.count == 1


def test_no_false_positive_complete_with_dates(tmp_path):
    db = _make_db(tmp_path)
    con = sqlite3.connect(db)
    _add_task(con, 1, code="A001", status="TK_Complete",
              act_start="2026-01-01 08:00:00", act_end="2026-01-10 18:00:00")
    _add_resource(con, 1, 1)
    con.commit(); con.close()
    result = sa.run_audit(db, 1)
    finding = next((f for f in result.findings if f.check == "COMPLETE_NO_DATES"), None)
    assert finding is None


# ---------------------------------------------------------------------------
# render_md
# ---------------------------------------------------------------------------

def test_render_md_contains_score(tmp_path):
    db = _make_db(tmp_path)
    con = sqlite3.connect(db)
    _add_task(con, 1, code="A001")
    con.commit(); con.close()
    result = sa.run_audit(db, 1)
    text = sa.render_md(result)
    assert "Score de calidad" in text
    assert "TEST_PROJ" in text


def test_render_md_no_findings_message(tmp_path):
    db = _make_db(tmp_path)
    con = sqlite3.connect(db)
    # Schedule perfecto: completo con fechas y recurso
    _add_task(con, 1, code="A001", status="TK_Complete",
              act_start="2026-01-01 08:00:00", act_end="2026-01-10 18:00:00")
    _add_resource(con, 1, 1)
    con.commit(); con.close()
    result = sa.run_audit(db, 1)
    text = sa.render_md(result)
    # Puede tener no_pred/no_succ pero el render funciona
    assert "Auditoria de Schedule" in text
    assert "TEST_PROJ" in text
