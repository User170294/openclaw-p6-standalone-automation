#!/usr/bin/env python3
"""
run_planner_kit.py
------------------
Orquestador end-to-end del flujo semanal de control P6.

Flujo completo:
  1. Validar que los proj_id existen en la DB y corresponden al tipo esperado.
  2. (Opcional) Generar Excel de captura semanal desde DB.
  3. (Opcional) Cargar avances desde Excel de captura a DB.
  4. Calcular EVM (PV desde baseline, EV desde programa actualizado).
  5. Generar reporte final (xlsx o md).

Uso minimo (solo EVM + reporte):
    python run_planner_kit.py \\
        --db <ruta.db> \\
        --pv-proj-id <proj_id_baseline> \\
        --ev-proj-id <proj_id_actualizado> \\
        --cutoff <YYYY-MM-DD> \\
        --out-dir <directorio_salida>

Uso completo (con captura + carga):
    python run_planner_kit.py \\
        --db <ruta.db> \\
        --pv-proj-id <proj_id_baseline> \\
        --ev-proj-id <proj_id_actualizado> \\
        --cutoff <YYYY-MM-DD> \\
        --iso-week <YYYY-W##> \\
        --capture-xlsx <ruta_captura.xlsx> \\
        --load \\
        --out-dir <directorio_salida> \\
        --format xlsx \\
        --project-name "Mi Proyecto"
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import subprocess
import sys
from datetime import datetime
from pathlib import Path

SCRIPTS_ROOT = Path(__file__).resolve().parents[1]
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

from p6_utils import open_db
from db_discovery import discover_projects, validate_pair


# ---------------------------------------------------------------------------
# Pasos del flujo
# ---------------------------------------------------------------------------

def step_generate_capture(db: Path, ev_proj_id: int, iso_week: str, out_dir: Path, project_name: str) -> Path:
    """Paso 2: genera Excel de captura semanal."""
    out_xlsx = out_dir / f"{ev_proj_id}_capture_{iso_week.replace(':', '-')}.xlsx"
    script = SCRIPTS_ROOT / "core" / "generate_progress_capture_excel.py"
    cmd = [
        sys.executable, str(script),
        "--db", str(db),
        "--proj-id", str(ev_proj_id),
        "--iso-week", iso_week,
        "--out", str(out_xlsx),
    ]
    print(f"\n[2/5] Generando Excel de captura → {out_xlsx.name}")
    result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
    if result.returncode != 0:
        raise SystemExit(f"❌ generate_progress_capture_excel falló:\n{result.stderr}")
    print(f"     ✓ {out_xlsx.name}")
    return out_xlsx


def step_load_progress(db: Path, capture_xlsx: Path, ev_proj_id: int) -> None:
    """Paso 3: carga avances desde Excel a DB (con backup automático)."""
    script = SCRIPTS_ROOT / "core" / "load_progress_excel_to_p6db.py"
    cmd = [
        sys.executable, str(script),
        "--db", str(db),
        "--xlsx", str(capture_xlsx),
        "--proj-id", str(ev_proj_id),
        "--apply",
    ]
    print(f"\n[3/5] Cargando avances desde {capture_xlsx.name} → DB")
    result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
    if result.returncode != 0:
        raise SystemExit(f"❌ load_progress_excel_to_p6db falló:\n{result.stderr}")
    print(f"     ✓ Carga aplicada")
    if result.stdout:
        for line in result.stdout.strip().splitlines():
            print(f"     {line}")


def step_run_evm(db: Path, pv_proj_id: int, ev_proj_id: int, cutoff: str, out_dir: Path) -> dict:
    """Paso 4: calcula EVM y retorna el dict compare() del engine."""
    script = SCRIPTS_ROOT / "core" / "pv_engine.py"
    json_out = out_dir / f"evm_{pv_proj_id}_{ev_proj_id}_{cutoff}.json"
    cmd = [
        sys.executable, str(script),
        "--db", str(db),
        "--proj-id", str(pv_proj_id),
        "--cutoff", cutoff,
        "--mode", "logic",
        "--out-dir", str(out_dir),
        "--format", "json",
    ]
    print(f"\n[4/5] Calculando EVM — PV desde [{pv_proj_id}] / EV desde [{ev_proj_id}]")

    # Regla de dos programas: --baseline-proj-id = PV, --proj-id = EV/Remaining
    cmd_ev = [
        sys.executable, str(script),
        "--db", str(db),
        "--proj-id", str(ev_proj_id),
        "--baseline-proj-id", str(pv_proj_id),
        "--cutoff", cutoff,
        "--mode", "logic",
        "--out-dir", str(out_dir),
        "--format", "json",
    ]
    result = subprocess.run(cmd_ev, capture_output=True, text=True, encoding="utf-8")
    if result.returncode != 0:
        raise SystemExit(f"❌ pv_engine (EV) falló:\n{result.stderr}")

    # Buscar el json generado (el engine genera con timestamp)
    json_files = sorted(out_dir.glob("pv_engine_logic_*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not json_files:
        raise SystemExit("❌ pv_engine no generó archivo JSON de salida.")

    report = json.loads(json_files[0].read_text(encoding="utf-8"))
    print(f"     ✓ EVM calculado — {report.get('row_count', 0)} semanas")
    if report.get("rows"):
        bac = report.get("bac", 0) or 1
        # Buscar el row del corte (último con ev_cum > 0); no usar rows[-1] que es la semana final del forecast
        cutoff_row = None
        for r in reversed(report["rows"]):
            if (r.get("ev_cum") or 0) > 0:
                cutoff_row = r
                break
        cutoff_row = cutoff_row or report["rows"][-1]
        print(f"     BAC: {bac:,.1f} HH | EV: {cutoff_row.get('ev_cum', 0):,.1f} HH ({cutoff_row.get('ev_pct', 0):.2f}%) | SPI al corte: {cutoff_row.get('spi', 'N/A')}")
    return report


def step_generate_narrative(report: dict, out_dir: Path, project_name: str, cutoff: str) -> Path:
    """Paso 5b: genera resumen ejecutivo en lenguaje natural."""
    from narrative_report import generate_narrative
    text = generate_narrative(report, project_name=project_name, cutoff=cutoff)
    stamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    out_path = out_dir / f"narrative_{stamp}.md"
    out_path.write_text(text, encoding="utf-8")
    print(f"     ✓ Narrativa: {out_path.name}")
    return out_path


def step_generate_report(report: dict, out_dir: Path, fmt: str, project_name: str, cutoff: str) -> Path:
    """Paso 5: genera reporte final."""
    script = SCRIPTS_ROOT / "core" / "report_generator.py"
    # Serializar report a JSON temporal
    tmp_json = out_dir / "_tmp_evm_report.json"
    tmp_json.write_text(json.dumps(report, ensure_ascii=False, default=str), encoding="utf-8")

    cmd = [
        sys.executable, str(script),
        "--input-json", str(tmp_json),
        "--out-dir", str(out_dir),
        "--format", fmt,
        "--project-name", project_name,
    ]
    print(f"\n[5/5] Generando reporte {fmt.upper()} → {out_dir.name}/")
    result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
    tmp_json.unlink(missing_ok=True)

    if result.returncode != 0:
        raise SystemExit(f"❌ report_generator falló:\n{result.stderr}")

    out_line = next((l for l in result.stdout.splitlines() if l.startswith("OUT=")), "")
    out_path = Path(out_line.replace("OUT=", "").strip()) if out_line else out_dir
    print(f"     ✓ {out_path.name if out_line else 'reporte generado'}")
    return out_path


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(
        description="Orquestador end-to-end del flujo semanal de control P6.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    # Requeridos siempre
    ap.add_argument("--db", required=True, help="Ruta a DB SQLite de P6")
    ap.add_argument("--pv-proj-id", type=int, required=True, help="PROJ_ID del programa baseline (fuente de PV)")
    ap.add_argument("--ev-proj-id", type=int, required=True, help="PROJ_ID del programa actualizado (fuente de EV)")
    ap.add_argument("--cutoff", required=True, help="Fecha de corte YYYY-MM-DD")
    ap.add_argument("--out-dir", default="data/reports", help="Directorio de salida (default: data/reports)")

    # Opcionales
    ap.add_argument("--iso-week", default=None, help="Semana ISO YYYY-W## para captura (ej. 2026-W12)")
    ap.add_argument("--capture-xlsx", default=None, help="Excel de captura existente para cargar avances")
    ap.add_argument("--load", action="store_true", help="Si se indica, aplica la carga de avances a la DB")
    ap.add_argument("--format", choices=["xlsx", "md"], default="xlsx", help="Formato del reporte final (default: xlsx)")
    ap.add_argument("--project-name", default="", help="Nombre del proyecto para el reporte")
    ap.add_argument("--generate-capture", action="store_true", help="Generar Excel de captura semanal antes de calcular EVM")
    return ap.parse_args()


def main() -> None:
    args = parse_args()
    db = Path(args.db)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 60)
    print("  P6 Planner Kit — Flujo semanal de control EVM")
    print("=" * 60)

    # --- Paso 1: Validar proj_ids ---
    print("\n[1/5] Validando programas en DB...")
    ev_info, pv_info = validate_pair(db, args.ev_proj_id, args.pv_proj_id)

    project_name = args.project_name or ev_info.short_name or f"PROJ_{args.ev_proj_id}"
    print(f"     ✓ Baseline : [{pv_info.proj_id}] {pv_info.short_name}")
    print(f"     ✓ Actualiz.: [{ev_info.proj_id}] {ev_info.short_name} (recalc: {ev_info.last_recalc or 'N/D'})")

    # --- Paso 2 (opcional): Generar Excel de captura ---
    if args.generate_capture:
        if not args.iso_week:
            raise SystemExit("❌ --iso-week requerido cuando se usa --generate-capture")
        step_generate_capture(db, args.ev_proj_id, args.iso_week, out_dir, project_name)
    else:
        print("\n[2/5] Captura Excel — omitida (usa --generate-capture para activar)")

    # --- Paso 3 (opcional): Cargar avances ---
    if args.capture_xlsx and args.load:
        step_load_progress(db, Path(args.capture_xlsx), args.ev_proj_id)
    else:
        print("\n[3/5] Carga de avances — omitida (usa --capture-xlsx + --load para activar)")

    # --- Paso 4: Calcular EVM ---
    report = step_run_evm(db, args.pv_proj_id, args.ev_proj_id, args.cutoff, out_dir)

    # --- Paso 5: Generar reporte + narrativa ---
    out_report = step_generate_report(report, out_dir, args.format, project_name, args.cutoff)
    out_narrative = step_generate_narrative(report, out_dir, project_name, args.cutoff)

    print("\n" + "=" * 60)
    print(f"  ✅ Flujo completado — {project_name}")
    print(f"  Reporte  : {out_report}")
    print(f"  Narrativa: {out_narrative}")
    print("=" * 60)


if __name__ == "__main__":
    main()
