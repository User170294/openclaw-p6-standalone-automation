#!/usr/bin/env python3
"""
schedule_audit.py
-----------------
Fingerprint y diagnostico de calidad de un schedule P6 desde DB SQLite.

Analiza la estructura del programa y detecta problemas comunes:
- Actividades sin predecesora (excepto hitos de inicio)
- Actividades sin sucesora (excepto hitos de fin)
- Actividades con duracion sospechosamente larga
- Actividades con restricciones de fecha (constraints)
- Actividades con lag negativo
- Balance de recursos labor vs sin recursos
- Actividades completadas sin fecha real de inicio o fin
- Consistencia TASK vs TASKRSRC

Uso:
    python schedule_audit.py --db <ruta.db> --proj-id <PROJ_ID>
    python schedule_audit.py --db <ruta.db> --proj-id <PROJ_ID> --out audit.md

Importable:
    from schedule_audit import run_audit
    result = run_audit(db_path, proj_id)
"""
from __future__ import annotations

import argparse
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any
import sys

SCRIPTS_ROOT = Path(__file__).resolve().parents[1]
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

from p6_utils import open_db


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

@dataclass
class AuditFinding:
    check: str          # ID del check
    severity: str       # "error" | "warning" | "info"
    count: int
    description: str
    examples: list[str] = field(default_factory=list)  # primeros N ejemplos

    @property
    def icon(self) -> str:
        return {"error": "ERROR", "warning": "WARN ", "info": "INFO "}.get(self.severity, "?????")


@dataclass
class AuditResult:
    proj_id: int
    proj_name: str
    total_tasks: int
    findings: list[AuditFinding] = field(default_factory=list)
    stats: dict[str, Any] = field(default_factory=dict)

    @property
    def errors(self) -> list[AuditFinding]:
        return [f for f in self.findings if f.severity == "error"]

    @property
    def warnings(self) -> list[AuditFinding]:
        return [f for f in self.findings if f.severity == "warning"]

    @property
    def score(self) -> int:
        """Score de calidad 0-100. 100 = sin hallazgos."""
        penalty = sum(f.count for f in self.errors) * 3
        penalty += sum(f.count for f in self.warnings) * 1
        base = max(0, 100 - penalty)
        return min(100, base)


# ---------------------------------------------------------------------------
# Checks
# ---------------------------------------------------------------------------

def _check_no_predecessor(cur: sqlite3.Cursor, proj_id: int, max_examples: int = 5) -> AuditFinding:
    """Actividades sin predecesora que no son hitos de inicio ni LOE."""
    rows = cur.execute("""
        SELECT t.TASK_CODE, t.TASK_NAME, t.TASK_TYPE
        FROM TASK t
        LEFT JOIN TASKPRED tp ON tp.TASK_ID = t.TASK_ID
        WHERE t.PROJ_ID = ?
          AND tp.TASK_ID IS NULL
          AND t.TASK_TYPE NOT IN ('TT_Mile', 'TT_FinMile', 'TT_LOE', 'TT_WBS')
          AND (t.STATUS_CODE IS NULL OR t.STATUS_CODE != 'TK_Complete')
        ORDER BY t.TASK_CODE
    """, (proj_id,)).fetchall()
    examples = [f"{r['TASK_CODE']} — {r['TASK_NAME']}" for r in rows[:max_examples]]
    return AuditFinding(
        check="NO_PREDECESSOR",
        severity="warning" if len(rows) <= 3 else "error",
        count=len(rows),
        description="Actividades sin predecesora (excepto hitos/LOE completados)",
        examples=examples,
    )


def _check_no_successor(cur: sqlite3.Cursor, proj_id: int, max_examples: int = 5) -> AuditFinding:
    """Actividades sin sucesora que no son hitos de fin ni LOE."""
    rows = cur.execute("""
        SELECT t.TASK_CODE, t.TASK_NAME, t.TASK_TYPE
        FROM TASK t
        LEFT JOIN TASKPRED tp2 ON tp2.PRED_TASK_ID = t.TASK_ID
        WHERE t.PROJ_ID = ?
          AND tp2.PRED_TASK_ID IS NULL
          AND t.TASK_TYPE NOT IN ('TT_Mile', 'TT_FinMile', 'TT_LOE', 'TT_WBS')
          AND (t.STATUS_CODE IS NULL OR t.STATUS_CODE != 'TK_Complete')
        ORDER BY t.TASK_CODE
    """, (proj_id,)).fetchall()
    examples = [f"{r['TASK_CODE']} — {r['TASK_NAME']}" for r in rows[:max_examples]]
    return AuditFinding(
        check="NO_SUCCESSOR",
        severity="warning" if len(rows) <= 3 else "error",
        count=len(rows),
        description="Actividades sin sucesora (excepto hitos/LOE completados)",
        examples=examples,
    )


def _check_long_duration(cur: sqlite3.Cursor, proj_id: int, threshold_days: int = 30, max_examples: int = 5) -> AuditFinding:
    """Actividades con duracion target mayor al umbral en dias habiles."""
    threshold_hrs = threshold_days * 8.0
    rows = cur.execute("""
        SELECT t.TASK_CODE, t.TASK_NAME,
               ROUND(t.TARGET_DRTN_HR_CNT / 8.0, 1) AS duration_days
        FROM TASK t
        WHERE t.PROJ_ID = ?
          AND t.TASK_TYPE NOT IN ('TT_LOE', 'TT_WBS')
          AND t.TARGET_DRTN_HR_CNT > ?
          AND (t.STATUS_CODE IS NULL OR t.STATUS_CODE != 'TK_Complete')
        ORDER BY t.TARGET_DRTN_HR_CNT DESC
    """, (proj_id, threshold_hrs)).fetchall()
    examples = [f"{r['TASK_CODE']} — {r['TASK_NAME']} ({r['duration_days']} dias)" for r in rows[:max_examples]]
    return AuditFinding(
        check="LONG_DURATION",
        severity="warning",
        count=len(rows),
        description=f"Actividades con duracion > {threshold_days} dias habiles",
        examples=examples,
    )


def _check_constraints(cur: sqlite3.Cursor, proj_id: int, max_examples: int = 5) -> AuditFinding:
    """Actividades con restricciones de fecha (constraints) que pueden romper la red."""
    rows = cur.execute("""
        SELECT t.TASK_CODE, t.TASK_NAME, t.CSTR_TYPE, t.CSTR_DATE
        FROM TASK t
        WHERE t.PROJ_ID = ?
          AND t.CSTR_TYPE IS NOT NULL
          AND t.CSTR_TYPE NOT IN ('CS_ALAP', 'CS_ASAP', '')
          AND (t.STATUS_CODE IS NULL OR t.STATUS_CODE != 'TK_Complete')
        ORDER BY t.TASK_CODE
    """, (proj_id,)).fetchall()
    examples = [f"{r['TASK_CODE']} — {r['CSTR_TYPE']} {(r['CSTR_DATE'] or '')[:10]}" for r in rows[:max_examples]]
    return AuditFinding(
        check="HARD_CONSTRAINTS",
        severity="warning",
        count=len(rows),
        description="Actividades con restricciones de fecha (pueden bloquear la red logica)",
        examples=examples,
    )


def _check_negative_lag(cur: sqlite3.Cursor, proj_id: int, max_examples: int = 5) -> AuditFinding:
    """Relaciones con lag negativo (avance artificial)."""
    rows = cur.execute("""
        SELECT t.TASK_CODE, t.TASK_NAME,
               tp.LAG_HR_CNT,
               tp2.TASK_CODE AS SUCC_CODE
        FROM TASKPRED tp
        JOIN TASK t ON t.TASK_ID = tp.PRED_TASK_ID AND t.PROJ_ID = ?
        JOIN TASK tp2 ON tp2.TASK_ID = tp.TASK_ID
        WHERE tp.LAG_HR_CNT < 0
        ORDER BY tp.LAG_HR_CNT ASC
    """, (proj_id,)).fetchall()
    examples = [
        f"{r['TASK_CODE']} -> {r['SUCC_CODE']} (lag: {round(r['LAG_HR_CNT']/8, 1)} dias)"
        for r in rows[:max_examples]
    ]
    return AuditFinding(
        check="NEGATIVE_LAG",
        severity="warning",
        count=len(rows),
        description="Relaciones con lag negativo (puede enmascarar atrasos reales)",
        examples=examples,
    )


def _check_no_resources(cur: sqlite3.Cursor, proj_id: int, max_examples: int = 5) -> AuditFinding:
    """Actividades de tipo Task sin ninguna asignacion de recurso labor."""
    rows = cur.execute("""
        SELECT t.TASK_CODE, t.TASK_NAME
        FROM TASK t
        LEFT JOIN TASKRSRC tr ON tr.TASK_ID = t.TASK_ID
            AND tr.PROJ_ID = t.PROJ_ID
            AND tr.RSRC_TYPE = 'RT_Labor'
        WHERE t.PROJ_ID = ?
          AND t.TASK_TYPE = 'TT_Task'
          AND tr.TASKRSRC_ID IS NULL
          AND (t.STATUS_CODE IS NULL OR t.STATUS_CODE != 'TK_Complete')
        ORDER BY t.TASK_CODE
    """, (proj_id,)).fetchall()
    examples = [f"{r['TASK_CODE']} — {r['TASK_NAME']}" for r in rows[:max_examples]]
    return AuditFinding(
        check="NO_LABOR_RESOURCE",
        severity="info",
        count=len(rows),
        description="Actividades tipo Task sin recurso labor asignado (sin HH en EVM)",
        examples=examples,
    )


def _check_complete_no_dates(cur: sqlite3.Cursor, proj_id: int, max_examples: int = 5) -> AuditFinding:
    """Actividades marcadas como completadas sin fecha real de inicio o fin."""
    rows = cur.execute("""
        SELECT TASK_CODE, TASK_NAME, ACT_START_DATE, ACT_END_DATE
        FROM TASK
        WHERE PROJ_ID = ?
          AND STATUS_CODE = 'TK_Complete'
          AND (ACT_START_DATE IS NULL OR ACT_END_DATE IS NULL)
        ORDER BY TASK_CODE
    """, (proj_id,)).fetchall()
    examples = [
        f"{r['TASK_CODE']} — inicio: {r['ACT_START_DATE'] or 'NULL'} / fin: {r['ACT_END_DATE'] or 'NULL'}"
        for r in rows[:max_examples]
    ]
    return AuditFinding(
        check="COMPLETE_NO_DATES",
        severity="error",
        count=len(rows),
        description="Actividades completadas sin fecha real de inicio o fin",
        examples=examples,
    )


def _get_stats(cur: sqlite3.Cursor, proj_id: int) -> dict[str, Any]:
    """Estadisticas generales del programa."""
    total = cur.execute("SELECT COUNT(*) FROM TASK WHERE PROJ_ID=? AND TASK_TYPE='TT_Task'", (proj_id,)).fetchone()[0]
    completed = cur.execute(
        "SELECT COUNT(*) FROM TASK WHERE PROJ_ID=? AND TASK_TYPE='TT_Task' AND STATUS_CODE='TK_Complete'", (proj_id,)
    ).fetchone()[0]
    in_progress = cur.execute(
        "SELECT COUNT(*) FROM TASK WHERE PROJ_ID=? AND TASK_TYPE='TT_Task' AND STATUS_CODE='TK_Active'", (proj_id,)
    ).fetchone()[0]
    not_started = cur.execute(
        "SELECT COUNT(*) FROM TASK WHERE PROJ_ID=? AND TASK_TYPE='TT_Task' AND (STATUS_CODE IS NULL OR STATUS_CODE='TK_NotStart')", (proj_id,)
    ).fetchone()[0]
    milestones = cur.execute(
        "SELECT COUNT(*) FROM TASK WHERE PROJ_ID=? AND TASK_TYPE IN ('TT_Mile','TT_FinMile')", (proj_id,)
    ).fetchone()[0]
    relations = cur.execute(
        "SELECT COUNT(*) FROM TASKPRED tp JOIN TASK t ON t.TASK_ID=tp.TASK_ID WHERE t.PROJ_ID=?", (proj_id,)
    ).fetchone()[0]
    bac = cur.execute(
        "SELECT COALESCE(SUM(TARGET_QTY),0) FROM TASKRSRC WHERE PROJ_ID=? AND RSRC_TYPE='RT_Labor'", (proj_id,)
    ).fetchone()[0]
    plan_start = cur.execute("SELECT MIN(TARGET_START_DATE) FROM TASK WHERE PROJ_ID=? AND TASK_TYPE='TT_Task'", (proj_id,)).fetchone()[0]
    plan_end = cur.execute("SELECT MAX(TARGET_END_DATE) FROM TASK WHERE PROJ_ID=? AND TASK_TYPE='TT_Task'", (proj_id,)).fetchone()[0]

    return {
        "total_tasks": total,
        "completed": completed,
        "in_progress": in_progress,
        "not_started": not_started,
        "milestones": milestones,
        "relations": relations,
        "bac_hh": round(float(bac), 1),
        "plan_start": (plan_start or "")[:10],
        "plan_end": (plan_end or "")[:10],
        "pct_complete": round(completed / total * 100, 1) if total else 0,
    }


# ---------------------------------------------------------------------------
# Main audit runner
# ---------------------------------------------------------------------------

def run_audit(db_path: Path, proj_id: int, long_duration_days: int = 30) -> AuditResult:
    """Corre todos los checks y retorna AuditResult."""
    con = open_db(db_path)
    con.row_factory = sqlite3.Row
    cur = con.cursor()

    row = cur.execute(
        "SELECT PROJ_SHORT_NAME FROM PROJECT WHERE PROJ_ID=?", (proj_id,)
    ).fetchone()
    if not row:
        con.close()
        raise ValueError(f"PROJ_ID {proj_id} no encontrado en la DB.")

    proj_name = row["PROJ_SHORT_NAME"] or f"PROJ_{proj_id}"
    stats = _get_stats(cur, proj_id)

    findings = [
        _check_no_predecessor(cur, proj_id),
        _check_no_successor(cur, proj_id),
        _check_long_duration(cur, proj_id, long_duration_days),
        _check_constraints(cur, proj_id),
        _check_negative_lag(cur, proj_id),
        _check_no_resources(cur, proj_id),
        _check_complete_no_dates(cur, proj_id),
    ]
    con.close()

    return AuditResult(
        proj_id=proj_id,
        proj_name=proj_name,
        total_tasks=stats["total_tasks"],
        findings=[f for f in findings if f.count > 0],
        stats=stats,
    )


# ---------------------------------------------------------------------------
# Render
# ---------------------------------------------------------------------------

def render_md(result: AuditResult) -> str:
    s = result.stats
    lines = [
        f"# Auditoria de Schedule — {result.proj_name}",
        f"*PROJ_ID: {result.proj_id} | Score de calidad: {result.score}/100*",
        "",
        "## Estadisticas generales",
        f"| Campo | Valor |",
        f"|-------|-------|",
        f"| Actividades totales (TT_Task) | {s['total_tasks']} |",
        f"| Completadas | {s['completed']} ({s['pct_complete']}%) |",
        f"| En curso | {s['in_progress']} |",
        f"| No iniciadas | {s['not_started']} |",
        f"| Hitos | {s['milestones']} |",
        f"| Relaciones logicas | {s['relations']} |",
        f"| BAC (HH labor) | {s['bac_hh']:,.1f} |",
        f"| Inicio planificado | {s['plan_start'] or 'N/D'} |",
        f"| Fin planificado | {s['plan_end'] or 'N/D'} |",
        "",
    ]

    if not result.findings:
        lines += ["## Hallazgos", "", "No se detectaron problemas. Schedule en buen estado."]
        return "\n".join(lines)

    errors = result.errors
    warnings = result.warnings
    infos = [f for f in result.findings if f.severity == "info"]

    if errors:
        lines += [f"## Errores ({len(errors)} checks con problemas criticos)", ""]
        for f in errors:
            lines.append(f"### [{f.check}] {f.description}")
            lines.append(f"**{f.count} actividades afectadas**")
            if f.examples:
                lines.append("Ejemplos:")
                for ex in f.examples:
                    lines.append(f"- {ex}")
            lines.append("")

    if warnings:
        lines += [f"## Advertencias ({len(warnings)} checks)", ""]
        for f in warnings:
            lines.append(f"### [{f.check}] {f.description}")
            lines.append(f"**{f.count} ocurrencias**")
            if f.examples:
                lines.append("Ejemplos:")
                for ex in f.examples:
                    lines.append(f"- {ex}")
            lines.append("")

    if infos:
        lines += [f"## Informativo ({len(infos)} checks)", ""]
        for f in infos:
            lines.append(f"### [{f.check}] {f.description}")
            lines.append(f"**{f.count} ocurrencias**")
            if f.examples:
                for ex in f.examples:
                    lines.append(f"- {ex}")
            lines.append("")

    lines += [
        "---",
        f"*Auditoria generada automaticamente por P6 Planner Kit.*",
    ]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="Auditoria de calidad de schedule P6 desde DB SQLite.")
    ap.add_argument("--db", required=True, help="Ruta a DB SQLite de P6")
    ap.add_argument("--proj-id", type=int, required=True, help="PROJ_ID a auditar")
    ap.add_argument("--out", default=None, help="Ruta de salida .md (default: imprime en consola)")
    ap.add_argument("--long-duration-days", type=int, default=30,
                    help="Umbral en dias para actividades con duracion larga (default: 30)")
    return ap.parse_args()


def main() -> None:
    args = parse_args()
    result = run_audit(Path(args.db), args.proj_id, args.long_duration_days)
    text = render_md(result)

    if args.out:
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(text, encoding="utf-8")
        print(f"OUT={out}")
        print(f"SCORE={result.score}")
        print(f"ERRORS={len(result.errors)}")
        print(f"WARNINGS={len(result.warnings)}")
    else:
        print(text)


if __name__ == "__main__":
    main()
