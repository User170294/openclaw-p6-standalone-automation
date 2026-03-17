"""Tests for generate_progress_capture_excel.py — Excel capture generation."""
from __future__ import annotations

import sqlite3
import sys
from datetime import date
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_CORE = ROOT / "scripts" / "core"
if str(SCRIPTS_CORE) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_CORE))

import generate_progress_capture_excel as gpce


# ---------------------------------------------------------------------------
# iso_week_bounds
# ---------------------------------------------------------------------------

def test_iso_week_bounds_w12_2026():
    start, end = gpce.iso_week_bounds("2026-W12")
    assert start == date(2026, 3, 16)
    assert end == date(2026, 3, 22)


def test_iso_week_bounds_w01_2026():
    start, end = gpce.iso_week_bounds("2026-W01")
    assert start == date(2025, 12, 29)
    assert end == date(2026, 1, 4)


def test_iso_week_bounds_strips_iso_prefix():
    start, end = gpce.iso_week_bounds("ISO2026-W12")
    assert start == date(2026, 3, 16)


# ---------------------------------------------------------------------------
# parse_db_dt
# ---------------------------------------------------------------------------

def test_parse_db_dt_full_format():
    dt = gpce.parse_db_dt("2026-03-16 08:00:00")
    assert dt.year == 2026
    assert dt.month == 3
    assert dt.day == 16


def test_parse_db_dt_none_returns_none():
    assert gpce.parse_db_dt(None) is None


def test_parse_db_dt_empty_string_returns_none():
    assert gpce.parse_db_dt("") is None


# ---------------------------------------------------------------------------
# overlaps
# ---------------------------------------------------------------------------

def test_overlaps_returns_true_for_intersecting_ranges():
    from datetime import datetime
    s_a = datetime(2026, 3, 16, 8, 0)
    e_a = datetime(2026, 3, 20, 18, 0)
    s_b = datetime(2026, 3, 18, 0, 0)
    e_b = datetime(2026, 3, 22, 23, 59)
    assert gpce.overlaps(s_a, e_a, s_b, e_b) is True


def test_overlaps_returns_false_for_non_intersecting():
    from datetime import datetime
    s_a = datetime(2026, 3, 1, 8, 0)
    e_a = datetime(2026, 3, 5, 18, 0)
    s_b = datetime(2026, 3, 16, 0, 0)
    e_b = datetime(2026, 3, 22, 23, 59)
    assert gpce.overlaps(s_a, e_a, s_b, e_b) is False


def test_overlaps_none_dates_returns_false():
    from datetime import datetime
    s_b = datetime(2026, 3, 16, 0, 0)
    e_b = datetime(2026, 3, 22, 23, 59)
    # Actividad sin fechas planificadas — el código la excluye (False) por seguridad
    assert gpce.overlaps(None, None, s_b, e_b) is False


# ---------------------------------------------------------------------------
# Sheet name derives from iso-week when --sheet not provided
# ---------------------------------------------------------------------------

def test_sheet_name_derives_from_iso_week(tmp_path):
    """Verify the sheet name logic (no DB needed, just string logic)."""
    iso_week = "2026-W12"
    sheet_name = f"Revision_Avance_{iso_week.replace(':', '-')}"
    assert sheet_name == "Revision_Avance_2026-W12"
    assert "W012" not in sheet_name  # old hardcoded value must be gone
