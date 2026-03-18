"""Tests for db_discovery.py — dynamic project discovery."""
from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_CORE = ROOT / "scripts" / "core"
if str(SCRIPTS_CORE) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_CORE))

import db_discovery as dd


# ---------------------------------------------------------------------------
# DB fixture helpers
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
        cur.execute(
            "INSERT INTO PROJECT VALUES (?,?,?,?,?,?,?)",
            (p["id"], p["name"], p.get("start"), p.get("end"),
             p.get("recalc"), p.get("sum_base"), p.get("orig")),
        )
    con.commit()
    con.close()
    return db


def _typical_db(tmp_path: Path) -> Path:
    return _make_db(tmp_path, [
        {"id": 100, "name": "Proyecto A",       "recalc": "2026-03-15", "sum_base": 101},
        {"id": 101, "name": "Proyecto A - B1",  "recalc": "2026-01-01", "orig": 100},
        {"id": 200, "name": "Proyecto B",       "recalc": "2026-02-10", "sum_base": 201},
        {"id": 201, "name": "Proyecto B - B1",  "recalc": "2025-12-01", "orig": 200},
        {"id": 300, "name": "Template",         "recalc": "2020-01-01"},  # autonomo
    ])


# ---------------------------------------------------------------------------
# discover_projects
# ---------------------------------------------------------------------------

def test_discover_assigns_active_role(tmp_path):
    db = _typical_db(tmp_path)
    projects = dd.discover_projects(db)
    active = [p for p in projects if p.proj_id == 100][0]
    assert active.role == "active"
    assert active.sum_base_proj_id == 101


def test_discover_assigns_baseline_role(tmp_path):
    db = _typical_db(tmp_path)
    projects = dd.discover_projects(db)
    baseline = [p for p in projects if p.proj_id == 101][0]
    assert baseline.role == "baseline"
    assert baseline.orig_proj_id == 100


def test_discover_assigns_autonomous_role(tmp_path):
    db = _typical_db(tmp_path)
    projects = dd.discover_projects(db)
    auto = [p for p in projects if p.proj_id == 300][0]
    assert auto.role == "autonomous"


def test_discover_enriches_baseline_name(tmp_path):
    db = _typical_db(tmp_path)
    projects = dd.discover_projects(db)
    active = [p for p in projects if p.proj_id == 100][0]
    assert active.baseline_name == "Proyecto A - B1"


def test_discover_enriches_active_name(tmp_path):
    db = _typical_db(tmp_path)
    projects = dd.discover_projects(db)
    baseline = [p for p in projects if p.proj_id == 101][0]
    assert baseline.active_name == "Proyecto A"


def test_discover_returns_all_projects(tmp_path):
    db = _typical_db(tmp_path)
    projects = dd.discover_projects(db)
    assert len(projects) == 5


# ---------------------------------------------------------------------------
# find_pairs
# ---------------------------------------------------------------------------

def test_find_pairs_detects_both_pairs(tmp_path):
    db = _typical_db(tmp_path)
    projects = dd.discover_projects(db)
    pairs = dd.find_pairs(projects)
    assert len(pairs) == 2


def test_find_pairs_active_and_baseline_correct(tmp_path):
    db = _typical_db(tmp_path)
    projects = dd.discover_projects(db)
    pairs = dd.find_pairs(projects)
    pair_ids = {(p.active.proj_id, p.baseline.proj_id) for p in pairs}
    assert (100, 101) in pair_ids
    assert (200, 201) in pair_ids


def test_find_pairs_empty_when_no_relations(tmp_path):
    db = _make_db(tmp_path, [
        {"id": 100, "name": "Solo A"},
        {"id": 200, "name": "Solo B"},
    ])
    projects = dd.discover_projects(db)
    pairs = dd.find_pairs(projects)
    assert pairs == []


# ---------------------------------------------------------------------------
# validate_pair
# ---------------------------------------------------------------------------

def test_validate_pair_returns_both_infos(tmp_path):
    db = _typical_db(tmp_path)
    updated, baseline = dd.validate_pair(db, 100, 101)
    assert updated.proj_id == 100
    assert baseline.proj_id == 101


def test_validate_pair_raises_if_updated_missing(tmp_path):
    db = _typical_db(tmp_path)
    with pytest.raises(SystemExit) as exc:
        dd.validate_pair(db, 999, 101)
    assert "999" in str(exc.value)


def test_validate_pair_raises_if_baseline_missing(tmp_path):
    db = _typical_db(tmp_path)
    with pytest.raises(SystemExit) as exc:
        dd.validate_pair(db, 100, 888)
    assert "888" in str(exc.value)


def test_validate_pair_raises_if_same_id(tmp_path):
    db = _typical_db(tmp_path)
    with pytest.raises(SystemExit) as exc:
        dd.validate_pair(db, 100, 100)
    assert "iguales" in str(exc.value)


def test_validate_pair_error_lists_available_projects(tmp_path):
    db = _typical_db(tmp_path)
    with pytest.raises(SystemExit) as exc:
        dd.validate_pair(db, 999, 101)
    msg = str(exc.value)
    assert "100" in msg  # lista programas disponibles
    assert "300" in msg


# ---------------------------------------------------------------------------
# ProjectInfo.display
# ---------------------------------------------------------------------------

def test_display_active_shows_lb(tmp_path):
    db = _typical_db(tmp_path)
    projects = dd.discover_projects(db)
    active = [p for p in projects if p.proj_id == 100][0]
    assert "activo" in active.display
    assert "101" in active.display


def test_display_baseline_shows_parent(tmp_path):
    db = _typical_db(tmp_path)
    projects = dd.discover_projects(db)
    baseline = [p for p in projects if p.proj_id == 101][0]
    assert "baseline" in baseline.display
    assert "100" in baseline.display


def test_display_autonomous(tmp_path):
    db = _typical_db(tmp_path)
    projects = dd.discover_projects(db)
    auto = [p for p in projects if p.proj_id == 300][0]
    assert "autonomo" in auto.display
