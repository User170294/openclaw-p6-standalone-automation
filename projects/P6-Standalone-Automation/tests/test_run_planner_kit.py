"""Tests for run_planner_kit.py — orchestrator and proj_id validation."""
from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_CORE = ROOT / "scripts" / "core"
if str(SCRIPTS_CORE) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_CORE))

import run_planner_kit as kit


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
            LAST_RECALC_DATE TEXT
        )
    """)
    for p in projects:
        cur.execute("INSERT INTO PROJECT VALUES (?,?,?)",
                    (p["id"], p["name"], p.get("recalc")))
    con.commit()
    con.close()
    return db


# ---------------------------------------------------------------------------
# validate_proj_id
# ---------------------------------------------------------------------------

def test_validate_proj_id_returns_metadata(tmp_path):
    db = _make_db(tmp_path, [{"id": 100, "name": "BASELINE", "recalc": "2026-03-15"}])
    info = kit.validate_proj_id(db, 100, "Baseline (PV)")
    assert info["proj_id"] == 100
    assert info["name"] == "BASELINE"
    assert info["last_recalc"] == "2026-03-15"


def test_validate_proj_id_raises_with_available_list(tmp_path):
    db = _make_db(tmp_path, [
        {"id": 100, "name": "BASELINE"},
        {"id": 200, "name": "UPDATED"},
    ])
    with pytest.raises(SystemExit) as exc_info:
        kit.validate_proj_id(db, 999, "Baseline (PV)")
    msg = str(exc_info.value)
    assert "999" in msg
    assert "100" in msg  # debe listar programas disponibles
    assert "200" in msg


def test_validate_proj_id_missing_db_raises(tmp_path):
    with pytest.raises(Exception):
        kit.validate_proj_id(tmp_path / "no_existe.db", 100, "test")


# ---------------------------------------------------------------------------
# validate_proj_ids_not_same
# ---------------------------------------------------------------------------

def test_validate_proj_ids_not_same_raises_when_equal():
    with pytest.raises(SystemExit) as exc_info:
        kit.validate_proj_ids_not_same(100, 100)
    assert "iguales" in str(exc_info.value)


def test_validate_proj_ids_not_same_passes_when_different():
    kit.validate_proj_ids_not_same(100, 200)  # no debe lanzar


# ---------------------------------------------------------------------------
# Regla de dos programas: mensaje claro
# ---------------------------------------------------------------------------

def test_error_message_mentions_pv_ev_rule():
    with pytest.raises(SystemExit) as exc_info:
        kit.validate_proj_ids_not_same(42, 42)
    msg = str(exc_info.value)
    assert "baseline" in msg.lower() or "pv" in msg.lower()
    assert "actualizado" in msg.lower() or "ev" in msg.lower()
