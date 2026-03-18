#!/usr/bin/env python3
"""
db_discovery.py
---------------
Descubrimiento dinámico de programas en una DB SQLite de P6 Standalone.

Consulta PROJECT para listar todos los programas disponibles, detecta
automáticamente cuáles son programas activos (con baseline asignado) y
cuáles son baselines, sin suponer nada sobre proj_ids ni nombres.

Uso interactivo:
    python db_discovery.py --db <ruta.db>

Uso como módulo:
    from db_discovery import discover_projects, find_pairs, validate_pair

Salida:
    Lista de programas con su relación baseline/actualizado inferida
    desde los campos SUM_BASE_PROJ_ID y ORIG_PROJ_ID de la tabla PROJECT.

Lógica de detección:
    - Programa activo  ->  SUM_BASE_PROJ_ID IS NOT NULL (tiene baseline asignado)
    - Baseline         ->  ORIG_PROJ_ID IS NOT NULL      (es copia de un programa activo)
    - Autonomo         ->  ambos NULL (sin relación baseline explícita)
"""
from __future__ import annotations

import argparse
import sqlite3
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional
import sys

SCRIPTS_ROOT = Path(__file__).resolve().parents[1]
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

from p6_utils import open_db


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

@dataclass
class ProjectInfo:
    proj_id: int
    short_name: str
    plan_start: Optional[str]
    plan_end: Optional[str]
    last_recalc: Optional[str]
    sum_base_proj_id: Optional[int]   # si tiene valor ->  es programa activo con esta LB
    orig_proj_id: Optional[int]       # si tiene valor ->  es baseline de este programa
    role: str = "autonomous"          # "active" | "baseline" | "autonomous"
    baseline_name: Optional[str] = None
    active_name: Optional[str] = None

    @property
    def is_active(self) -> bool:
        return self.role == "active"

    @property
    def is_baseline(self) -> bool:
        return self.role == "baseline"

    @property
    def display(self) -> str:
        if self.is_active:
            lb = f"LB ->  [{self.sum_base_proj_id}] {self.baseline_name or ''}"
            recalc = f" | recalc: {self.last_recalc[:10]}" if self.last_recalc else ""
            return f"[{self.proj_id:>6}] {self.short_name:<30} (activo){recalc} | {lb}"
        if self.is_baseline:
            active = f"baseline de [{self.orig_proj_id}] {self.active_name or ''}"
            return f"[{self.proj_id:>6}] {self.short_name:<30} (baseline) | {active}"
        recalc = f" | recalc: {self.last_recalc[:10]}" if self.last_recalc else ""
        return f"[{self.proj_id:>6}] {self.short_name:<30} (autonomo){recalc}"


@dataclass
class ProjectPair:
    active: ProjectInfo
    baseline: ProjectInfo

    @property
    def display(self) -> str:
        recalc = f" | corte: {self.active.last_recalc[:10]}" if self.active.last_recalc else ""
        return (
            f"  Activo   : [{self.active.proj_id}] {self.active.short_name}{recalc}\n"
            f"  Baseline : [{self.baseline.proj_id}] {self.baseline.short_name}"
        )


# ---------------------------------------------------------------------------
# Core functions
# ---------------------------------------------------------------------------

def discover_projects(db_path: Path) -> list[ProjectInfo]:
    """
    Lee todos los programas de la DB y les asigna rol (active/baseline/autonomous).
    No asume nada sobre nombres ni IDs.
    """
    con = open_db(db_path)
    con.row_factory = sqlite3.Row
    cur = con.cursor()

    rows = cur.execute("""
        SELECT PROJ_ID, PROJ_SHORT_NAME,
               PLAN_START_DATE, PLAN_END_DATE, LAST_RECALC_DATE,
               SUM_BASE_PROJ_ID, ORIG_PROJ_ID
        FROM PROJECT
        ORDER BY PROJ_ID
    """).fetchall()
    con.close()

    # Primer pasada: construir mapa básico
    projects: dict[int, ProjectInfo] = {}
    for r in rows:
        p = ProjectInfo(
            proj_id=int(r["PROJ_ID"]),
            short_name=(r["PROJ_SHORT_NAME"] or "").strip(),
            plan_start=r["PLAN_START_DATE"],
            plan_end=r["PLAN_END_DATE"],
            last_recalc=r["LAST_RECALC_DATE"],
            sum_base_proj_id=int(r["SUM_BASE_PROJ_ID"]) if r["SUM_BASE_PROJ_ID"] else None,
            orig_proj_id=int(r["ORIG_PROJ_ID"]) if r["ORIG_PROJ_ID"] else None,
        )
        if p.sum_base_proj_id is not None:
            p.role = "active"
        elif p.orig_proj_id is not None:
            p.role = "baseline"
        projects[p.proj_id] = p

    # Segunda pasada: enriquecer con nombres cruzados
    for p in projects.values():
        if p.is_active and p.sum_base_proj_id in projects:
            p.baseline_name = projects[p.sum_base_proj_id].short_name
        if p.is_baseline and p.orig_proj_id in projects:
            p.active_name = projects[p.orig_proj_id].short_name

    return list(projects.values())


def find_pairs(projects: list[ProjectInfo]) -> list[ProjectPair]:
    """
    Retorna todos los pares (activo, baseline) detectados automáticamente.
    """
    index = {p.proj_id: p for p in projects}
    pairs = []
    for p in projects:
        if p.is_active and p.sum_base_proj_id in index:
            baseline = index[p.sum_base_proj_id]
            if baseline.is_baseline:
                pairs.append(ProjectPair(active=p, baseline=baseline))
    return pairs


def validate_pair(
    db_path: Path,
    updated_proj_id: int,
    baseline_proj_id: int,
) -> tuple[ProjectInfo, ProjectInfo]:
    """
    Valida que ambos proj_id existen en la DB y son distintos.
    Retorna (updated_info, baseline_info) o lanza SystemExit con mensaje claro.
    """
    projects = discover_projects(db_path)
    index = {p.proj_id: p for p in projects}

    errors = []
    if updated_proj_id not in index:
        errors.append(f"  ❌ --ev-proj-id {updated_proj_id} no existe en la DB")
    if baseline_proj_id not in index:
        errors.append(f"  ❌ --pv-proj-id {baseline_proj_id} no existe en la DB")

    if errors:
        available = "\n".join(f"  [{p.proj_id:>6}] {p.short_name}" for p in projects)
        raise SystemExit(
            "\n".join(errors) +
            f"\n\nProgramas disponibles:\n{available}"
        )

    if updated_proj_id == baseline_proj_id:
        raise SystemExit(
            f"\n❌ --ev-proj-id y --pv-proj-id son iguales ({updated_proj_id}).\n"
            "La regla de dos programas requiere programas distintos:\n"
            "  --pv-proj-id ->  programa baseline (línea base)\n"
            "  --ev-proj-id ->  programa actualizado (avance real)"
        )

    return index[updated_proj_id], index[baseline_proj_id]


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _print_discovery(db_path: Path) -> None:
    projects = discover_projects(db_path)
    pairs = find_pairs(projects)

    print(f"\n{'='*70}")
    print(f"  DB: {db_path.name}")
    print(f"  Programas encontrados: {len(projects)}")
    print(f"{'='*70}\n")

    # Mostrar pares detectados primero
    if pairs:
        print(f"-- Pares activo/baseline detectados ({len(pairs)}) ----------------------\n")
        for i, pair in enumerate(pairs, 1):
            print(f"Par #{i}")
            print(pair.display)
            print()

    # Programas sin relación
    autonomous = [p for p in projects if p.role == "autonomous"]
    if autonomous:
        print(f"-- Programas autonomos (sin baseline asignado) ({len(autonomous)}) ------\n")
        for p in autonomous:
            print(f"  {p.display}")
        print()

    # Baselines huérfanos (apuntan a un activo que no existe)
    orphan_baselines = [
        p for p in projects
        if p.is_baseline and p.orig_proj_id not in {q.proj_id for q in projects}
    ]
    if orphan_baselines:
        print(f"-- Baselines huérfanos ({len(orphan_baselines)}) ----------------------\n")
        for p in orphan_baselines:
            print(f"  {p.display}")
        print()

    print("Para trabajar con un par, usa:")
    print("  python run_planner_kit.py --db <DB> --pv-proj-id <LB_ID> --ev-proj-id <ACTIVO_ID> --cutoff YYYY-MM-DD")
    print()


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(
        description="Descubre y lista programas disponibles en una DB SQLite de P6.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument("--db", required=True, help="Ruta a la DB SQLite de P6")
    ap.add_argument("--json", action="store_true", help="Salida en JSON (para integración con otros scripts)")
    return ap.parse_args()


def main() -> None:
    args = parse_args()
    db_path = Path(args.db)

    if not db_path.exists():
        raise SystemExit(f"❌ DB no encontrada: {db_path}")

    if args.json:
        import json
        projects = discover_projects(db_path)
        pairs = find_pairs(projects)
        out = {
            "projects": [
                {
                    "proj_id": p.proj_id,
                    "short_name": p.short_name,
                    "role": p.role,
                    "sum_base_proj_id": p.sum_base_proj_id,
                    "orig_proj_id": p.orig_proj_id,
                    "last_recalc": p.last_recalc,
                    "baseline_name": p.baseline_name,
                    "active_name": p.active_name,
                }
                for p in projects
            ],
            "pairs": [
                {
                    "active_proj_id": pair.active.proj_id,
                    "active_name": pair.active.short_name,
                    "baseline_proj_id": pair.baseline.proj_id,
                    "baseline_name": pair.baseline.short_name,
                    "last_recalc": pair.active.last_recalc,
                }
                for pair in pairs
            ],
        }
        print(json.dumps(out, ensure_ascii=False, indent=2))
    else:
        _print_discovery(db_path)


if __name__ == "__main__":
    main()
