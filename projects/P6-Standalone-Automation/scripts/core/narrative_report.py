#!/usr/bin/env python3
"""
narrative_report.py
-------------------
Genera un resumen ejecutivo en lenguaje natural a partir del output de pv_engine.compare().

El resumen interpreta los KPIs y comunica el estado del proyecto en texto plano,
sin requerir que el planificador interprete tablas o índices.

Uso:
    python narrative_report.py --input-json <ruta_evm.json> [--project-name "Mi Proyecto"] [--cutoff YYYY-MM-DD]
    python narrative_report.py --input-json <ruta_evm.json> --out <ruta_salida.md>

También importable como módulo:
    from narrative_report import generate_narrative
    text = generate_narrative(report_dict, project_name="Mi Proyecto", cutoff="2026-03-15")
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any


# ---------------------------------------------------------------------------
# Helpers de interpretación
# ---------------------------------------------------------------------------

def _fmt(value: Any, decimals: int = 1) -> str:
    if value is None:
        return "N/D"
    try:
        return f"{float(value):,.{decimals}f}"
    except Exception:
        return str(value)


def _pct(value: Any) -> str:
    if value is None:
        return "N/D"
    try:
        return f"{float(value):.1f}%"
    except Exception:
        return str(value)


def _interpret_spi(spi: float | None) -> str:
    if spi is None:
        return "no disponible"
    if spi >= 1.05:
        return "adelantado respecto al plan"
    if spi >= 0.95:
        return "en línea con el plan"
    if spi >= 0.80:
        return "con atraso moderado"
    if spi >= 0.65:
        return "con atraso significativo"
    return "con atraso crítico"


def _interpret_cpi(cpi: float | None) -> str:
    if cpi is None:
        return None
    if cpi >= 1.05:
        return "con mejor eficiencia de la planificada"
    if cpi >= 0.95:
        return "con eficiencia dentro de lo esperado"
    if cpi >= 0.80:
        return "con eficiencia por debajo de lo planificado"
    return "con eficiencia significativamente inferior a lo planificado"


def _trend_sentence(rows: list[dict]) -> str:
    """Analiza las últimas 3 semanas para detectar tendencia de SPI."""
    if len(rows) < 2:
        return ""
    recent = [r for r in rows[-3:] if r.get("spi") is not None]
    if len(recent) < 2:
        return ""
    spis = [float(r["spi"]) for r in recent]
    delta = spis[-1] - spis[0]
    if delta > 0.03:
        return "La tendencia de las últimas semanas es de **mejora**."
    if delta < -0.03:
        return "La tendencia de las últimas semanas es de **deterioro**."
    return "El desempeño se ha mantenido **estable** en las últimas semanas."


def _forecast_sentence(report: dict, bac: float) -> str:
    rows = report.get("rows", [])
    if not rows:
        return ""
    last = rows[-1]
    fc = last.get("forecast_cum") or 0.0
    fc_pct = last.get("forecast_pct")
    eac = report.get("eac")

    parts = []
    if fc and bac:
        gap = round(fc - bac, 1)
        if abs(gap) < bac * 0.01:
            parts.append(f"El pronóstico actual apunta a cerrar **en el presupuesto** ({_fmt(fc)} HH).")
        elif gap > 0:
            parts.append(f"El pronóstico actual es de **{_fmt(fc)} HH**, un sobrecosto de {_fmt(gap)} HH respecto al BAC.")
        else:
            parts.append(f"El pronóstico actual es de **{_fmt(fc)} HH**, {_fmt(abs(gap))} HH por debajo del BAC.")

    if eac and eac != fc:
        parts.append(f"El EAC calculado por CPI es {_fmt(eac)} HH.")

    return " ".join(parts)


def _top_weeks(rows: list[dict], n: int = 3) -> list[dict]:
    """Retorna las n semanas con menor SPI (peor desempeño)."""
    with_spi = [r for r in rows if r.get("spi") is not None]
    return sorted(with_spi, key=lambda r: float(r["spi"]))[:n]


# ---------------------------------------------------------------------------
# Generador principal
# ---------------------------------------------------------------------------

def generate_narrative(
    report: dict[str, Any],
    project_name: str = "",
    cutoff: str = "",
) -> str:
    """
    Genera un resumen ejecutivo en texto plano a partir del dict de pv_engine.compare().
    Retorna el texto en formato Markdown.
    """
    rows = report.get("rows", [])
    last = rows[-1] if rows else {}
    bac = float(report.get("bac") or 0)
    pv = float(report.get("pv") or last.get("pv_cum") or 0)
    ev = float(report.get("ev") or last.get("ev_cum") or 0)
    ac = float(report.get("ac") or last.get("ac_cum") or 0)
    sv = report.get("sv") or last.get("sv")
    spi = last.get("spi")
    cpi = report.get("cpi")
    eac = report.get("eac")
    etc = report.get("etc")
    ev_pct = last.get("ev_pct") or (ev / bac * 100 if bac else None)
    pv_pct = last.get("pv_pct") or (pv / bac * 100 if bac else None)

    title = project_name or "Proyecto"
    cutoff_txt = f" al corte {cutoff}" if cutoff else ""

    lines: list[str] = []

    # Encabezado
    lines.append(f"# Resumen ejecutivo — {title}")
    lines.append(f"*Generado automáticamente{cutoff_txt}*")
    lines.append("")

    # Estado general
    spi_label = _interpret_spi(float(spi) if spi is not None else None)
    lines.append("## Estado general")
    lines.append(
        f"El proyecto se encuentra **{spi_label}** con un avance real de **{_pct(ev_pct)}** "
        f"({_fmt(ev)} HH) contra un avance planificado de **{_pct(pv_pct)}** ({_fmt(pv)} HH) "
        f"sobre un presupuesto total de **{_fmt(bac)} HH**."
    )
    lines.append("")

    # KPIs
    lines.append("## Indicadores clave")
    lines.append(f"| Indicador | Valor | Interpretación |")
    lines.append(f"|-----------|-------|----------------|")
    lines.append(f"| BAC | {_fmt(bac)} HH | Presupuesto total del proyecto |")
    lines.append(f"| PV | {_fmt(pv)} HH ({_pct(pv_pct)}) | Trabajo planificado al corte |")
    lines.append(f"| EV | {_fmt(ev)} HH ({_pct(ev_pct)}) | Trabajo realmente ejecutado |")
    if ac:
        lines.append(f"| AC | {_fmt(ac)} HH | Horas reales consumidas |")
    if sv is not None:
        sv_txt = f"{_fmt(sv)} HH {'(atraso)' if float(sv) < 0 else '(adelanto)'}"
        lines.append(f"| SV | {sv_txt} | Desviación de cronograma |")
    if spi is not None:
        lines.append(f"| SPI | {_fmt(float(spi), 3)} | {_interpret_spi(float(spi)).capitalize()} |")
    if cpi is not None:
        lines.append(f"| CPI | {_fmt(float(cpi), 3)} | {(_interpret_cpi(float(cpi)) or '').capitalize()} |")
    if eac is not None:
        lines.append(f"| EAC | {_fmt(eac)} HH | Estimado de costo final |")
    if etc is not None:
        lines.append(f"| ETC | {_fmt(etc)} HH | Trabajo restante proyectado |")
    lines.append("")

    # Desviación
    lines.append("## Análisis de desviación")
    if sv is not None and float(sv) < 0:
        lines.append(
            f"Existe un atraso de **{_fmt(abs(float(sv)))} HH** respecto al plan. "
            f"Esto representa el {_pct(abs(float(sv)) / bac * 100 if bac else None)} del BAC total."
        )
    elif sv is not None and float(sv) >= 0:
        lines.append(
            f"El proyecto lleva **{_fmt(float(sv))} HH de adelanto** respecto al plan."
        )
    else:
        lines.append("No hay información suficiente para calcular la desviación.")

    trend = _trend_sentence(rows)
    if trend:
        lines.append(trend)
    lines.append("")

    # Pronóstico
    fc_txt = _forecast_sentence(report, bac)
    if fc_txt:
        lines.append("## Pronóstico")
        lines.append(fc_txt)
        lines.append("")

    # Semanas con peor desempeño
    worst = _top_weeks(rows, 3)
    if worst:
        lines.append("## Semanas de menor desempeño")
        lines.append("Las semanas con menor SPI registrado:")
        lines.append("")
        lines.append("| Semana | EV acum (HH) | SPI |")
        lines.append("|--------|-------------|-----|")
        for r in worst:
            lines.append(f"| {r.get('week', '')} | {_fmt(r.get('ev_cum'))} | {_fmt(r.get('spi'), 3)} |")
        lines.append("")

    # Cierre
    lines.append("## Conclusión")
    conclusion_parts = [f"El proyecto presenta un SPI de **{_fmt(float(spi), 3)}**" if spi else ""]
    cpi_note = _interpret_cpi(float(cpi)) if cpi else None
    if cpi_note:
        conclusion_parts.append(f"y una eficiencia de costo {cpi_note}")
    if conclusion_parts[0]:
        lines.append(". ".join(p for p in conclusion_parts if p) + ".")

    if eac and bac:
        gap = float(eac) - bac
        if gap > bac * 0.05:
            lines.append(f"De mantenerse la eficiencia actual, el proyecto cerraría con un sobrecosto estimado de **{_fmt(gap)} HH**.")
        elif gap < -bac * 0.02:
            lines.append(f"De mantenerse la eficiencia actual, el proyecto cerraría **{_fmt(abs(gap))} HH por debajo del presupuesto**.")
        else:
            lines.append("De mantenerse la eficiencia actual, el proyecto cerraría **dentro del presupuesto**.")

    lines.append("")
    lines.append("---")
    lines.append("*Reporte generado automáticamente por P6 Planner Kit.*")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="Genera resumen ejecutivo en lenguaje natural desde output de pv_engine.")
    ap.add_argument("--input-json", required=True, help="JSON generado por pv_engine --format json")
    ap.add_argument("--project-name", default="", help="Nombre del proyecto")
    ap.add_argument("--cutoff", default="", help="Fecha de corte YYYY-MM-DD")
    ap.add_argument("--out", default=None, help="Ruta de salida .md (default: imprime en consola)")
    return ap.parse_args()


def main() -> None:
    args = parse_args()
    report = json.loads(Path(args.input_json).read_text(encoding="utf-8"))
    text = generate_narrative(report, project_name=args.project_name, cutoff=args.cutoff)

    if args.out:
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(text, encoding="utf-8")
        print(f"OUT={out}")
    else:
        print(text)


if __name__ == "__main__":
    main()
