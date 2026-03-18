"""Tests for generate_recovery_excel.py — calendar math and weekly HH logic."""
from __future__ import annotations

import sys
from datetime import date, datetime, timedelta
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_CORE = ROOT / "scripts" / "core"
if str(SCRIPTS_CORE) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_CORE))

import generate_recovery_excel as gre


# ---------------------------------------------------------------------------
# overlap_hours
# ---------------------------------------------------------------------------

def test_overlap_hours_full_overlap():
    a0 = datetime(2026, 3, 16, 8, 0)
    a1 = datetime(2026, 3, 16, 18, 0)
    b0 = datetime(2026, 3, 16, 8, 0)
    b1 = datetime(2026, 3, 16, 18, 0)
    assert gre.overlap_hours(a0, a1, b0, b1) == pytest.approx(10.0)


def test_overlap_hours_partial():
    a0 = datetime(2026, 3, 16, 8, 0)
    a1 = datetime(2026, 3, 16, 18, 0)
    b0 = datetime(2026, 3, 16, 13, 0)
    b1 = datetime(2026, 3, 16, 18, 0)
    assert gre.overlap_hours(a0, a1, b0, b1) == pytest.approx(5.0)


def test_overlap_hours_no_overlap():
    a0 = datetime(2026, 3, 16, 8, 0)
    a1 = datetime(2026, 3, 16, 12, 0)
    b0 = datetime(2026, 3, 16, 14, 0)
    b1 = datetime(2026, 3, 16, 18, 0)
    assert gre.overlap_hours(a0, a1, b0, b1) == 0.0


def test_overlap_hours_adjacent_no_overlap():
    a0 = datetime(2026, 3, 16, 8, 0)
    a1 = datetime(2026, 3, 16, 13, 0)
    b0 = datetime(2026, 3, 16, 13, 0)
    b1 = datetime(2026, 3, 16, 18, 0)
    assert gre.overlap_hours(a0, a1, b0, b1) == 0.0


# ---------------------------------------------------------------------------
# combine_dt / parse_clock
# ---------------------------------------------------------------------------

def test_combine_dt():
    d = date(2026, 3, 16)
    clk = gre.parse_clock("08:00")
    dt = gre.combine_dt(d, clk)
    assert dt == datetime(2026, 3, 16, 8, 0)


def test_parse_clock_returns_time():
    t = gre.parse_clock("14:30")
    assert t.hour == 14
    assert t.minute == 30


# ---------------------------------------------------------------------------
# parse_calendar_text
# ---------------------------------------------------------------------------

CALENDAR_WEEKDAYS = r"""(0||CalendarData()(
  (0||DaysOfWeek()(
    (0||1()())
    (0||2()(
      (0||0(s|08:00|f|13:00)())
      (0||1(s|14:00|f|18:00)())))
    (0||3()(
      (0||0(s|08:00|f|13:00)())
      (0||1(s|14:00|f|18:00)())))
    (0||4()(
      (0||0(s|08:00|f|13:00)())
      (0||1(s|14:00|f|18:00)())))
    (0||5()(
      (0||0(s|08:00|f|13:00)())
      (0||1(s|14:00|f|18:00)())))
    (0||6()(
      (0||0(s|08:00|f|13:00)())
      (0||1(s|14:00|f|18:00)())))
    (0||7()())))
  (0||Exceptions()())))"""


def test_parse_calendar_text_weekday_windows():
    cal = gre.parse_calendar_text(CALENDAR_WEEKDAYS)
    # Lunes = weekday 0 en Python = p6_day 2 → debe tener ventanas
    assert 0 in cal["weekday_windows"]
    windows = cal["weekday_windows"][0]
    assert len(windows) == 2
    # Primera ventana 08:00-13:00
    assert windows[0][0].hour == 8
    assert windows[0][1].hour == 13


def test_parse_calendar_text_sunday_has_no_windows():
    cal = gre.parse_calendar_text(CALENDAR_WEEKDAYS)
    # Domingo = weekday 6 en Python = p6_day 1 → sin ventanas
    assert 6 not in cal["weekday_windows"]


def test_parse_calendar_text_no_exceptions():
    cal = gre.parse_calendar_text(CALENDAR_WEEKDAYS)
    assert len(cal["exceptions"]) == 0


def test_parse_calendar_text_none_returns_empty():
    cal = gre.parse_calendar_text(None)
    assert cal["weekday_windows"] == {}
    assert len(cal["exceptions"]) == 0


# ---------------------------------------------------------------------------
# week_hh
# ---------------------------------------------------------------------------

def _make_calendar_lv() -> dict:
    """Calendario L-V con jornada partida 08:00-13:00 / 14:00-18:00 (9 HH/día)."""
    return gre.parse_calendar_text(CALENDAR_WEEKDAYS)


def test_week_hh_full_activity_in_week():
    """Actividad que cae 100% dentro de la semana objetivo."""
    cal = _make_calendar_lv()
    # W12: lunes 16-mar a domingo 22-mar (5 días laborales × 9 HH = 45 HH)
    remain_start = datetime(2026, 3, 16, 8, 0)
    end_dt = datetime(2026, 3, 20, 18, 0)  # viernes
    qty = 45.0
    result = gre.week_hh(remain_start, end_dt, qty, cal, date(2026, 3, 16), date(2026, 3, 22))
    assert result == pytest.approx(45.0, abs=0.01)


def test_week_hh_activity_spans_two_weeks():
    """Actividad que cruza dos semanas — solo retorna la fracción de la semana objetivo."""
    cal = _make_calendar_lv()
    # Actividad: lun 16-mar a vie 27-mar (2 semanas, 10 días laborales × 9 HH = 90 HH)
    remain_start = datetime(2026, 3, 16, 8, 0)
    end_dt = datetime(2026, 3, 27, 18, 0)
    qty = 90.0
    # Semana W12: 16-22 mar → 5 días de los 10 totales
    result = gre.week_hh(remain_start, end_dt, qty, cal, date(2026, 3, 16), date(2026, 3, 22))
    assert result == pytest.approx(45.0, abs=0.1)


def test_week_hh_activity_outside_week_returns_zero():
    """Actividad completamente fuera de la semana objetivo."""
    cal = _make_calendar_lv()
    remain_start = datetime(2026, 3, 2, 8, 0)
    end_dt = datetime(2026, 3, 6, 18, 0)
    qty = 45.0
    result = gre.week_hh(remain_start, end_dt, qty, cal, date(2026, 3, 16), date(2026, 3, 22))
    assert result == 0.0


def test_week_hh_zero_qty_returns_zero():
    cal = _make_calendar_lv()
    result = gre.week_hh(
        datetime(2026, 3, 16, 8, 0), datetime(2026, 3, 20, 18, 0),
        0.0, cal, date(2026, 3, 16), date(2026, 3, 22)
    )
    assert result == 0.0


def test_week_hh_none_calendar_returns_zero():
    """Sin calendario, no hay horas efectivas → 0."""
    result = gre.week_hh(
        datetime(2026, 3, 16, 8, 0), datetime(2026, 3, 20, 18, 0),
        45.0, None, date(2026, 3, 16), date(2026, 3, 22)
    )
    assert result == 0.0


# ---------------------------------------------------------------------------
# week_label (ISO universal)
# ---------------------------------------------------------------------------

def test_week_label_w12_2026():
    mon = date(2026, 3, 16)
    iso = mon.isocalendar()
    label = f"Y{iso.year % 100:02d}-W{iso.week:02d}"
    assert label == "Y26-W12"


def test_week_label_no_ot1844_reference():
    """Verificar que la generación de label no depende de fecha ancla de OT-1844."""
    mon = date(2025, 1, 6)  # W02 de 2025
    iso = mon.isocalendar()
    label = f"Y{iso.year % 100:02d}-W{iso.week:02d}"
    assert label == "Y25-W02"
    assert "2026" not in label
