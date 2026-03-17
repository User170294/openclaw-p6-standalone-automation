"""Tests for run_planner_kit.py — orchestrator validation via db_discovery."""
from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_CORE = ROOT / "scripts" / "core"
if str(SCRIPTS_CORE) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_CORE))

from db_discovery import validate_pair


# ---------------------------------------------------------------------------
# DB fixture
# ---------------------------------------------------------------------------

def _make_db(tmp_path: Path, projects: list[dict]) -> Path:
    db = tmp_path / "test.db"
    con = sqlite3.connect(db)
    cur = con.cursor()
    cur.execute("""
        CREATE TABLE PROJECT (
            PROJ_ID INTEGER PRIMARY KEY,
            PROJ_SHORT_NAME TEXT,
            PLAN_START_DATE TEXT,
            PLAN_END_DATE TEXT,
            LAST_RECALC_DATE TEXT,
            SUM_BASE_PROJ_ID INTEGER,
            ORIG_PROJ_ID INTEGER
        )
    """)
    for p in projects:
        cur.execute("INSERT INTO PROJECT VALUES (?,?,?,?,?,?,?)",
                    (p["id"], p["name"], None, None, p.get("recalc"),
                     p.get("sum_base"), p.get("orig")))
    con.commit()
    con.close()
    return db


# ---------------------------------------------------------------------------
# validate_pair (regla de dos programas)
# ---------------------------------------------------------------------------

def test_validate_pair_returns_metadata(tmp_path):
    db = _make_db(tmp_path, [
        {"id": 100, "name": "BASELINE",  "recalc": "2026-01-01"},
        {"id": 200, "name": "UPDATED",   "recalc": "2026-03-15"},
    ])
    updated, baseline = validate_pair(db, 200, 100)
    assert updated.proj_id == 200
    assert updated.short_name == "UPDATED"
    assert baseline.proj_id == 100
    assert baseline.short_name == "BASELINE"


def test_validate_pair_raises_with_available_list(tmp_path):
    db = _make_db(tmp_path, [
        {"id": 100, "name": "BASELINE"},
        {"id": 200, "name": "UPDATED"},
    ])
    with pytest.raises(SystemExit) as exc_info:
        validate_pair(db, 999, 100)
    msg = str(exc_info.value)
    assert "999" in msg
    assert "100" in msg
    assert "200" in msg


def test_validate_pair_raises_when_equal():
    from pathlib import Path
    import tempfile, os
    with tempfile.TemporaryDirectory() as td:
        db = _make_db(Path(td), [{"id": 100, "name": "PROJ"}])
        with pytest.raises(SystemExit) as exc_info:
            validate_pair(db, 100, 100)
        assert "iguales" in str(exc_info.value)


def test_validate_pair_error_message_mentions_pv_ev_rule(tmp_path):
    db = _make_db(tmp_path, [{"id": 100, "name": "PROJ"}])
    with pytest.raises(SystemExit) as exc_info:
        validate_pair(db, 100, 100)
    msg = str(exc_info.value).lower()
    assert "baseline" in msg or "pv" in msg
    assert "actualizado" in msg or "ev" in msg


def test_validate_pair_raises_if_baseline_missing(tmp_path):
    db = _make_db(tmp_path, [{"id": 200, "name": "UPDATED"}])
    with pytest.raises(SystemExit) as exc_info:
        validate_pair(db, 200, 888)
    assert "888" in str(exc_info.value)
