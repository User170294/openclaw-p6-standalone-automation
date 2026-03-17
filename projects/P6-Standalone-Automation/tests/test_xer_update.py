"""Tests for xer_update.py — XER patching logic."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_CORE = ROOT / "scripts" / "core"
if str(SCRIPTS_CORE) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_CORE))

import xer_update


# ---------------------------------------------------------------------------
# Minimal valid XER fixture
# ---------------------------------------------------------------------------

def _make_xer(tmp_path: Path, task_rows: list[str] = None, taskrsrc_rows: list[str] = None) -> Path:
    task_rows = task_rows or []
    taskrsrc_rows = taskrsrc_rows or []
    lines = [
        "ERMHDR\t19.12\t2026-01-01\tProject\tAdmin\t\t\t\t\t",
        "%T\tPROJECT",
        "%F\tproj_id\tproj_short_name",
        "%R\tPROJ_001\tTEST",
        "%T\tRSRC",
        "%F\trsrc_id\trsrc_short_name\trsrc_type",
        "%R\tRSRC_OP1\tOP1\tRT_Labor",
        "%R\tRSRC_OP2\tOP2\tRT_Labor",
        "%R\tRSRC_OP3\tOP3\tRT_Labor",
        "%T\tTASK",
        "%F\tproj_id\ttask_id\ttask_code\ttask_name\tstatus_code\tphys_complete_pct\tact_start_date\ttarget_work_qty\tact_work_qty\tremain_work_qty",
    ] + task_rows + [
        "%T\tTASKRSRC",
        "%F\tproj_id\ttask_id\trsrc_id\trsrc_type\ttarget_qty\tact_reg_qty\tremain_qty\tact_start_date\tact_end_date",
    ] + taskrsrc_rows + [
        "%E",
    ]
    xer_path = tmp_path / "test.xer"
    xer_path.write_text("\n".join(lines), encoding="utf-8")
    return xer_path


# ---------------------------------------------------------------------------
# parse_sections
# ---------------------------------------------------------------------------

def test_parse_sections_yields_project_row(tmp_path):
    xer = _make_xer(tmp_path)
    lines = xer.read_text(encoding="utf-8").splitlines()
    sections = list(xer_update.parse_sections(lines))
    tables = [s[1] for s in sections]
    assert "PROJECT" in tables
    assert "RSRC" in tables


def test_parse_sections_detects_task_rows(tmp_path):
    xer = _make_xer(tmp_path, task_rows=[
        "%R\tPROJ_001\tTASK_001\tA001\tTarea A\tTK_Active\t0\t\t100\t0\t100",
    ])
    lines = xer.read_text(encoding="utf-8").splitlines()
    sections = list(xer_update.parse_sections(lines))
    task_sections = [s for s in sections if s[1] == "TASK"]
    assert len(task_sections) == 1


# ---------------------------------------------------------------------------
# fmt helper
# ---------------------------------------------------------------------------

def test_fmt_integer_value():
    assert xer_update.fmt(100.0) == "100"


def test_fmt_decimal_strips_trailing_zeros():
    result = xer_update.fmt(3.5)
    assert result == "3.5"


def test_fmt_zero():
    assert xer_update.fmt(0.0) == "0"


# ---------------------------------------------------------------------------
# progress update — dry-run
# ---------------------------------------------------------------------------

def test_progress_update_dry_run_does_not_write(tmp_path, capsys):
    xer = _make_xer(tmp_path, task_rows=[
        "%R\tPROJ_001\tTASK_001\tA001\tMontaje estructura\tTK_NotStart\t0\t\t100\t0\t100",
    ], taskrsrc_rows=[
        "%R\tPROJ_001\tTASK_001\tRSRC_OP1\tRT_Labor\t100\t0\t100\t\t",
    ])
    out = tmp_path / "out.xer"
    sys.argv = [
        "xer_update.py",
        "--in", str(xer),
        "--out", str(out),
        "--progress-filter", "montaje",
        "--progress", "50",
        "--actual-start", "2026-03-01 08:00",
        "--dry-run",
    ]
    xer_update.main()
    # dry-run: NO escribe archivo, pero reporta en stdout
    assert not out.exists()
    captured = capsys.readouterr()
    assert "DRY_RUN" in captured.out
    assert "progress_tasks=1" in captured.out


def test_invalid_xer_raises_systemexit(tmp_path):
    bad = tmp_path / "bad.xer"
    bad.write_text("NOT A VALID XER", encoding="utf-8")
    out = tmp_path / "out.xer"
    sys.argv = ["xer_update.py", "--in", str(bad), "--out", str(out)]
    with pytest.raises(SystemExit):
        xer_update.main()


def test_xer_without_trailer_raises_systemexit(tmp_path):
    no_trailer = tmp_path / "notrail.xer"
    no_trailer.write_text("ERMHDR\t19.12\n%T\tPROJECT\n", encoding="utf-8")
    out = tmp_path / "out.xer"
    sys.argv = ["xer_update.py", "--in", str(no_trailer), "--out", str(out)]
    with pytest.raises(SystemExit):
        xer_update.main()
