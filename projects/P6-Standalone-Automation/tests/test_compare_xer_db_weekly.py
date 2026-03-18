"""Tests for compare_xer_db_weekly.py — CSV comparison logic."""
from __future__ import annotations

import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_CORE = ROOT / "scripts" / "core"
if str(SCRIPTS_CORE) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_CORE))

import compare_xer_db_weekly as cmp


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def write_csv(path: Path, rows: list[dict], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)


# ---------------------------------------------------------------------------
# load_csv
# ---------------------------------------------------------------------------

def test_load_csv_with_explicit_cum(tmp_path):
    p = tmp_path / "data.csv"
    write_csv(p, [
        {"week": "Y26-W01", "pv": "100", "acum": "100"},
        {"week": "Y26-W02", "pv": "200", "acum": "300"},
    ], ["week", "pv", "acum"])
    result = cmp.load_csv(p, "week", "pv", "acum")
    assert result["Y26-W01"]["value"] == 100.0
    assert result["Y26-W01"]["cum"] == 100.0
    assert result["Y26-W02"]["cum"] == 300.0


def test_load_csv_recalculates_cum_when_no_cum_col(tmp_path):
    p = tmp_path / "data.csv"
    write_csv(p, [
        {"week": "Y26-W01", "pv": "100"},
        {"week": "Y26-W02", "pv": "200"},
        {"week": "Y26-W03", "pv": "50"},
    ], ["week", "pv"])
    result = cmp.load_csv(p, "week", "pv", None)
    assert result["Y26-W03"]["cum"] == 350.0


def test_load_csv_skips_empty_week(tmp_path):
    p = tmp_path / "data.csv"
    write_csv(p, [
        {"week": "", "pv": "999", "acum": "999"},
        {"week": "Y26-W01", "pv": "100", "acum": "100"},
    ], ["week", "pv", "acum"])
    result = cmp.load_csv(p, "week", "pv", "acum")
    assert "" not in result
    assert len(result) == 1


# ---------------------------------------------------------------------------
# main() integration — CSV in, CSV out
# ---------------------------------------------------------------------------

def test_main_produces_correct_delta(tmp_path):
    xer_csv = tmp_path / "xer.csv"
    db_csv = tmp_path / "db.csv"
    out_csv = tmp_path / "out.csv"

    write_csv(xer_csv, [
        {"week": "Y26-W01", "pv": "100", "acum": "100"},
        {"week": "Y26-W02", "pv": "200", "acum": "300"},
    ], ["week", "pv", "acum"])

    write_csv(db_csv, [
        {"week": "Y26-W01", "pv": "110", "acum": "110"},
        {"week": "Y26-W02", "pv": "190", "acum": "300"},
    ], ["week", "pv", "acum"])

    import sys as _sys
    _sys.argv = [
        "compare_xer_db_weekly.py",
        "--xer-csv", str(xer_csv),
        "--db-csv", str(db_csv),
        "--out-csv", str(out_csv),
    ]
    cmp.main()

    with out_csv.open("r", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    w1 = next(r for r in rows if r["week"] == "Y26-W01")
    assert float(w1["delta_value"]) == pytest.approx(10.0, abs=0.001)
    assert float(w1["delta_cum"]) == pytest.approx(10.0, abs=0.001)

    w2 = next(r for r in rows if r["week"] == "Y26-W02")
    assert float(w2["delta_value"]) == pytest.approx(-10.0, abs=0.001)
    assert float(w2["delta_cum"]) == pytest.approx(0.0, abs=0.001)


def test_main_handles_week_only_in_one_source(tmp_path):
    """Semana presente en DB pero ausente en XER debe aparecer con xer_value=0."""
    xer_csv = tmp_path / "xer.csv"
    db_csv = tmp_path / "db.csv"
    out_csv = tmp_path / "out.csv"

    write_csv(xer_csv, [
        {"week": "Y26-W01", "pv": "100", "acum": "100"},
    ], ["week", "pv", "acum"])

    write_csv(db_csv, [
        {"week": "Y26-W01", "pv": "100", "acum": "100"},
        {"week": "Y26-W02", "pv": "200", "acum": "300"},
    ], ["week", "pv", "acum"])

    import sys as _sys
    _sys.argv = [
        "compare_xer_db_weekly.py",
        "--xer-csv", str(xer_csv),
        "--db-csv", str(db_csv),
        "--out-csv", str(out_csv),
    ]
    cmp.main()

    with out_csv.open("r", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    assert len(rows) == 2
    w2 = next(r for r in rows if r["week"] == "Y26-W02")
    assert float(w2["xer_value"]) == pytest.approx(0.0, abs=0.001)
    assert float(w2["db_value"]) == pytest.approx(200.0, abs=0.001)


import pytest
