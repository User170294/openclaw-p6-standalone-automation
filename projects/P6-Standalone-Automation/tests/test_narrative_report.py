"""Tests for narrative_report.py — natural language EVM summary."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_CORE = ROOT / "scripts" / "core"
if str(SCRIPTS_CORE) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_CORE))

import narrative_report as nr


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _make_report(spi=0.88, cpi=0.95, ev=4500, bac=8100, pv=5100, ac=4700, eac=8526, etc=4026):
    return {
        "mode": "logic", "stub": False, "note": "Test",
        "bac": bac, "pv": pv, "ev": ev, "ac": ac,
        "sv": round(ev - pv, 2),
        "spi": None,  # viene en rows
        "cpi": cpi, "eac": eac, "etc": etc,
        "rows": [
            {"week": "Y26-W08", "pv_week": 1134, "pv_cum": 1134, "pv_pct": 14.0,
             "ev_cum": 1000, "ev_pct": 12.3, "ac_cum": 1050,
             "sv": -134, "spi": 0.88, "forecast_cum": 7800, "forecast_pct": 96.3},
            {"week": "Y26-W09", "pv_week": 1161, "pv_cum": 2295, "pv_pct": 28.3,
             "ev_cum": 2100, "ev_pct": 25.9, "ac_cum": 2200,
             "sv": -195, "spi": 0.91, "forecast_cum": 7900, "forecast_pct": 97.5},
            {"week": "Y26-W10", "pv_week": 1476, "pv_cum": 3771, "pv_pct": 46.6,
             "ev_cum": 3395, "ev_pct": 41.9, "ac_cum": 3500,
             "sv": -376, "spi": round(spi, 6), "forecast_cum": 8200, "forecast_pct": 101.2},
        ],
    }


# ---------------------------------------------------------------------------
# interpret_spi
# ---------------------------------------------------------------------------

def test_interpret_spi_on_track():
    assert "línea" in nr._interpret_spi(1.00)

def test_interpret_spi_ahead():
    assert "adelantado" in nr._interpret_spi(1.10)

def test_interpret_spi_moderate_delay():
    assert "moderado" in nr._interpret_spi(0.88)

def test_interpret_spi_critical():
    assert "crítico" in nr._interpret_spi(0.50)

def test_interpret_spi_none():
    assert "no disponible" in nr._interpret_spi(None)


# ---------------------------------------------------------------------------
# interpret_cpi
# ---------------------------------------------------------------------------

def test_interpret_cpi_ok():
    assert "esperado" in nr._interpret_cpi(1.00)

def test_interpret_cpi_good():
    assert "mejor" in nr._interpret_cpi(1.10)

def test_interpret_cpi_bad():
    assert "debajo" in nr._interpret_cpi(0.85)

def test_interpret_cpi_none_returns_none():
    assert nr._interpret_cpi(None) is None


# ---------------------------------------------------------------------------
# trend_sentence
# ---------------------------------------------------------------------------

def test_trend_improving():
    rows = [
        {"spi": 0.80}, {"spi": 0.85}, {"spi": 0.92}
    ]
    assert "mejora" in nr._trend_sentence(rows)

def test_trend_deteriorating():
    rows = [
        {"spi": 0.95}, {"spi": 0.88}, {"spi": 0.82}
    ]
    assert "deterioro" in nr._trend_sentence(rows)

def test_trend_stable():
    rows = [
        {"spi": 0.90}, {"spi": 0.91}, {"spi": 0.90}
    ]
    assert "estable" in nr._trend_sentence(rows)

def test_trend_single_row_returns_empty():
    assert nr._trend_sentence([{"spi": 0.88}]) == ""


# ---------------------------------------------------------------------------
# generate_narrative — contenido
# ---------------------------------------------------------------------------

def test_narrative_contains_project_name():
    text = nr.generate_narrative(_make_report(), project_name="SAG Planta 3")
    assert "SAG Planta 3" in text

def test_narrative_contains_bac():
    text = nr.generate_narrative(_make_report(bac=8100))
    assert "8,100" in text

def test_narrative_contains_spi_value():
    text = nr.generate_narrative(_make_report(spi=0.88))
    assert "0.880" in text

def test_narrative_contains_delay_interpretation():
    text = nr.generate_narrative(_make_report(spi=0.88))
    assert "atraso" in text.lower() or "moderado" in text.lower()

def test_narrative_contains_kpi_table():
    text = nr.generate_narrative(_make_report())
    assert "BAC" in text
    assert "SPI" in text
    assert "EAC" in text
    assert "ETC" in text

def test_narrative_contains_worst_weeks():
    text = nr.generate_narrative(_make_report())
    assert "Y26-W08" in text  # semana con SPI más bajo

def test_narrative_contains_conclusion():
    text = nr.generate_narrative(_make_report())
    assert "## Conclusión" in text

def test_narrative_contains_forecast():
    text = nr.generate_narrative(_make_report())
    assert "## Pronóstico" in text

def test_narrative_with_cutoff():
    text = nr.generate_narrative(_make_report(), cutoff="2026-03-15")
    assert "2026-03-15" in text

def test_narrative_ahead_of_plan():
    text = nr.generate_narrative(_make_report(spi=1.10, ev=5500, pv=4500))
    assert "adelant" in text.lower()

def test_narrative_returns_non_empty_string():
    text = nr.generate_narrative(_make_report())
    assert isinstance(text, str)
    assert len(text) > 200
