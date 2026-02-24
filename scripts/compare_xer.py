"""
compare_xer.py
Compara dos XER de Primavera P6: línea base vs actualizado.
Genera resumen de avance, actividades retrasadas, completadas y en ejecución.

Uso:
    python scripts/compare_xer.py \
        --baseline projects/OT-1844/docs/schedule/ot1844_revB.xer \
        --actual   projects/OT-1844/docs/schedule/ot1844_W09.xer \
        --cutoff   2026-02-22 \
        --out      projects/OT-1844/docs/schedule/
"""

import argparse
import csv
import json
from datetime import datetime
from pathlib import Path


# ─── Parser XER ───────────────────────────────────────────────────────────────
def parse_xer(path: Path) -> dict:
    tables: dict = {}
    current = None
    fields: list = []
    with path.open("r", encoding="latin-1", errors="replace") as f:
        for raw in f:
            line = raw.rstrip("\n\r")
            if not line:
                continue
            parts = line.split("\t")
            tag = parts[0]
            if tag == "%T":
                current = parts[1]
                tables[current] = {"fields": [], "rows": []}
                fields = []
            elif tag == "%F" and current:
                fields = parts[1:]
                tables[current]["fields"] = fields
            elif tag == "%R" and current:
                vals = parts[1:]
                if len(vals) < len(fields):
                    vals += [""] * (len(fields) - len(vals))
                tables[current]["rows"].append(dict(zip(fields, vals)))
    return tables


def to_dt(s: str) -> datetime | None:
    for fmt in ("%Y-%m-%d %H:%M", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(s, fmt)
        except (ValueError, TypeError):
            pass
    return None


def to_f(x, default=0.0) -> float:
    try:
        return float(x)
    except Exception:
        return default


def extract_tasks(tables: dict) -> dict:
    wbs_rows = tables.get("PROJWBS", {}).get("rows", [])
    wbs_map = {r["wbs_id"]: r.get("wbs_name") or r.get("wbs_short_name", "") for r in wbs_rows}
    tasks = {}
    for t in tables.get("TASK", {}).get("rows", []):
        code = t.get("task_code", "")
        tasks[code] = {
            "code": code,
            "name": t.get("task_name", ""),
            "status": t.get("status_code", ""),      # TK_NotStart, TK_Active, TK_Complete
            "type": t.get("task_type", ""),
            "wbs": wbs_map.get(t.get("wbs_id", ""), ""),
            "early_start": t.get("early_start_date", ""),
            "early_end": t.get("early_end_date", ""),
            "target_start": t.get("target_start_date", ""),
            "target_end": t.get("target_end_date", ""),
            "act_start": t.get("act_start_date", ""),
            "act_end": t.get("act_end_date", ""),
            "phys_pct": to_f(t.get("phys_complete_pct"), 0.0),
            "float_hr": to_f(t.get("total_float_hr_cnt"), 0.0),
            "remain_hr": to_f(t.get("remain_drtn_hr_cnt"), 0.0),
            "driving": (t.get("driving_path_flag") or "").upper() == "Y",
        }
    return tasks


# ─── Main ─────────────────────────────────────────────────────────────────────
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--baseline", required=True)
    ap.add_argument("--actual", required=True)
    ap.add_argument("--cutoff", default=datetime.today().strftime("%Y-%m-%d"),
                    help="Fecha de corte ISO (YYYY-MM-DD)")
    ap.add_argument("--curva-s", default=None,
                    help="CSV de curva S planificada (Semana,Periodo_Fin,HH_Acumulado,Pct_Acumulado). "
                         "Si se provee, el PV oficial se toma de aquí.")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    cutoff = datetime.strptime(args.cutoff, "%Y-%m-%d").replace(hour=23, minute=59)
    out = Path(args.out)

    # Curva S oficial (opcional): leer PV y BAC desde el CSV si se provee
    curva_s_pv_pct: float | None = None
    curva_s_bac_hh: float | None = None
    if args.curva_s:
        cs_path = Path(args.curva_s)
        if cs_path.exists():
            with cs_path.open("r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                best_row = None
                for row in reader:
                    periodo_fin = datetime.strptime(row["Periodo_Fin"], "%Y-%m-%d").replace(hour=23, minute=59)
                    if periodo_fin <= cutoff:
                        best_row = row
                if best_row:
                    curva_s_pv_pct = float(best_row["Pct_Acumulado"])
                    # BAC = HH_Acumulado del último registro del CSV
                # BAC total = última fila
            with cs_path.open("r", encoding="utf-8") as f:
                rows = list(csv.DictReader(f))
                if rows:
                    curva_s_bac_hh = float(rows[-1]["HH_Acumulado"])
    out.mkdir(parents=True, exist_ok=True)

    bl_tables = parse_xer(Path(args.baseline))
    ac_tables = parse_xer(Path(args.actual))

    bl_tasks = extract_tasks(bl_tables)
    ac_tasks = extract_tasks(ac_tables)

    bl_proj = (bl_tables.get("PROJECT", {}) or {}).get("rows", [{}])[0]
    ac_proj = (ac_tables.get("PROJECT", {}) or {}).get("rows", [{}])[0]

    # ── Clasificación por estado actual ───────────────────────────────────────
    completed, in_progress, not_started_late, not_started_ok, delayed = [], [], [], [], []

    all_codes = set(ac_tasks) | set(bl_tasks)
    for code in all_codes:
        ac = ac_tasks.get(code)
        bl = bl_tasks.get(code)
        if not ac:
            continue
        if ac["type"] not in {"TT_Task", "TT_Rsrc"}:
            continue

        status = ac["status"]
        # Fechas objetivo (de línea base)
        bl_end = to_dt((bl or ac).get("target_end") or (bl or ac).get("early_end"))
        ac_end = to_dt(ac.get("early_end"))
        act_end = to_dt(ac.get("act_end"))

        if status == "TK_Complete":
            completed.append(ac)
        elif status == "TK_Active":
            # ¿está retrasada respecto a línea base?
            slipped = (bl_end and ac_end and ac_end > bl_end)
            rec = dict(ac, slipped=slipped,
                       bl_end=bl_end.strftime("%Y-%m-%d") if bl_end else "",
                       ac_end_cur=ac_end.strftime("%Y-%m-%d") if ac_end else "")
            in_progress.append(rec)
            if slipped:
                delayed.append(rec)
        elif status == "TK_NotStart":
            if bl_end and bl_end <= cutoff:
                not_started_late.append(ac)
            else:
                not_started_ok.append(ac)

    # ── Valor Ganado (EV) ponderado por HH ────────────────────────────────────
    # Método correcto: EV = Σ(phys_pct × target_drtn_hr) / BAC
    # PV al corte = HH planificadas acumuladas hasta cutoff / BAC
    # (distribuidas linealmente dentro del rango target_start → target_end de cada tarea)

    # Recuperar target_drtn_hr_cnt directamente del XER actual
    ac_drtn: dict[str, float] = {}
    for t in ac_tables.get("TASK", {}).get("rows", []):
        code = t.get("task_code", "")
        ac_drtn[code] = to_f(t.get("target_drtn_hr_cnt"), 0.0)

    bl_drtn: dict[str, float] = {}
    for t in bl_tables.get("TASK", {}).get("rows", []):
        code = t.get("task_code", "")
        bl_drtn[code] = to_f(t.get("target_drtn_hr_cnt"), 0.0)

    total_tasks = [t for t in ac_tasks.values() if t["type"] == "TT_Task"]
    n_total = len(total_tasks)
    n_complete = len([t for t in total_tasks if t["status"] == "TK_Complete"])
    n_active = len([t for t in total_tasks if t["status"] == "TK_Active"])

    # BAC: suma de HH planeadas (baseline) de todas las TT_Task
    bac = sum(bl_drtn.get(t["code"], ac_drtn.get(t["code"], 0.0))
              for t in ac_tasks.values() if t["type"] == "TT_Task")

    # EV: valor ganado = Σ(phys_pct/100 × target_drtn_hr) usando HH reales actualizadas
    ev_hh = sum(
        (t["phys_pct"] / 100.0) * ac_drtn.get(t["code"], 0.0)
        for t in ac_tasks.values()
        if t["type"] == "TT_Task"
    )
    pct_ev = round(ev_hh / bac * 100, 2) if bac else 0.0

    # PV al corte: distribución lineal de HH de cada tarea baseline en el rango target_start→target_end
    # Si la tarea termina antes del corte → 100% de sus HH cuentan como PV
    # Si la tarea aún no inicia al corte → 0%
    # Si el corte cae dentro → proporción lineal
    pv_hh = 0.0
    for t in bl_tasks.values():
        if t["type"] != "TT_Task":
            continue
        hh = bl_drtn.get(t["code"], 0.0)
        if hh == 0:
            continue
        ts = to_dt(t.get("target_start") or t.get("early_start"))
        te = to_dt(t.get("target_end") or t.get("early_end"))
        if ts is None or te is None:
            continue
        if te <= cutoff:
            pv_hh += hh
        elif ts > cutoff:
            pv_hh += 0.0
        else:
            duration = (te - ts).total_seconds()
            elapsed = (cutoff - ts).total_seconds()
            ratio = max(0.0, min(1.0, elapsed / duration)) if duration > 0 else 0.0
            pv_hh += hh * ratio

    # Si hay curva S oficial, usar su PV (más preciso que interpolación lineal)
    if curva_s_pv_pct is not None:
        pct_planned = round(curva_s_pv_pct, 2)
        pv_hh_ref = round(pct_planned / 100 * (curva_s_bac_hh or bac), 1)
        bac_ref = curva_s_bac_hh or bac
        # Recalcular EV con mismo BAC de la curva S para que los % sean comparables
        pct_ev = round(ev_hh / bac * 100, 2)   # EV% vs BAC tarea (consistente internamente)
        # Nota: si BAC curva S ≠ BAC tareas, los % no son estrictamente comparables;
        # usamos curva S PV% y EV% calculado con BAC tareas como aproximación.
    else:
        pv_hh_ref = round(pv_hh, 1)
        bac_ref = bac
        pct_planned = round((pv_hh_ref / bac_ref * 100), 2) if bac_ref else 0.0

    delta_pct = round(pct_ev - pct_planned, 2)

    # ── Hitos próximos ────────────────────────────────────────────────────────
    milestones = sorted(
        [t for t in ac_tasks.values()
         if t["type"] in {"TT_FinMile", "TT_Mile"} and t.get("early_end")],
        key=lambda x: x["early_end"]
    )

    # ── Resumen dict ─────────────────────────────────────────────────────────
    summary = {
        "cutoff": args.cutoff,
        "baseline_xer": args.baseline,
        "actual_xer": args.actual,
        "last_schedule_date": ac_proj.get("last_schedule_date", ""),
        "n_total_tasks": n_total,
        "n_complete": n_complete,
        "n_active": n_active,
        "n_not_started_late": len(not_started_late),
        "n_delayed": len(delayed),
        "bac_hh": round(bac_ref, 1),
        "pv_hh": pv_hh_ref,
        "ev_hh": round(ev_hh, 1),
        "pct_planned_pv": pct_planned,
        "pct_ev_real": pct_ev,
        "delta_pct_ev_pv": delta_pct,
        "pv_source": "curva_s_csv" if curva_s_pv_pct is not None else "interpolacion_lineal_xer",
    }

    # ── Exportar JSON ─────────────────────────────────────────────────────────
    report = {
        "summary": summary,
        "completed": completed,
        "in_progress": in_progress,
        "not_started_late": not_started_late,
        "milestones_upcoming": milestones[:10],
    }
    json_out = out / "w09_comparison.json"
    with json_out.open("w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    # ── Exportar CSV actividades en retraso ───────────────────────────────────
    delay_csv = out / "w09_delayed.csv"
    delay_fields = ["code", "name", "wbs", "status", "bl_end", "ac_end_cur", "phys_pct", "float_hr"]
    with delay_csv.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=delay_fields, extrasaction="ignore")
        w.writeheader()
        for row in sorted(not_started_late + delayed, key=lambda x: x.get("bl_end", "")):
            w.writerow({k: row.get(k, "") for k in delay_fields})

    # ── Markdown ──────────────────────────────────────────────────────────────
    md = out / "w09_comparison.md"
    with md.open("w", encoding="utf-8") as f:
        f.write(f"# OT-1844 — Comparación Línea Base vs Real | Corte S8 ({args.cutoff})\n\n")
        f.write(f"- **Última programación (real):** {summary['last_schedule_date']}\n")
        f.write(f"- **Total actividades (TT_Task):** {n_total}\n")
        f.write(f"- **Completadas:** {n_complete}\n")
        f.write(f"- **En ejecución:** {n_active}\n")
        f.write(f"- **No iniciadas con retraso:** {len(not_started_late)}\n")
        f.write(f"- **En ejecución con retraso vs LB:** {len(delayed)}\n\n")
        f.write(f"### Indicadores Valor Ganado (EVM)\n")
        f.write(f"| Indicador | HH | % |\n|-----------|-----|---|\n")
        f.write(f"| BAC (presupuesto total) | {summary['bac_hh']} HH | 100% |\n")
        f.write(f"| PV — Planificado al corte | {summary['pv_hh']} HH | **{pct_planned}%** |\n")
        f.write(f"| EV — Valor Ganado real | {summary['ev_hh']} HH | **{pct_ev}%** |\n")
        f.write(f"| **Δ EV − PV** | | **{delta_pct:+.2f}%** |\n\n")

        f.write("---\n\n## ✅ Actividades Completadas\n\n")
        if completed:
            f.write("| Código | Actividad | WBS | % Fís |\n|--------|-----------|-----|-------|\n")
            for t in sorted(completed, key=lambda x: x.get("act_end", "")):
                f.write(f"| {t['code']} | {t['name'][:60]} | {t['wbs'][:35]} | {t['phys_pct']:.0f}% |\n")
        else:
            f.write("_Ninguna_\n")

        f.write("\n---\n\n## 🔄 En Ejecución\n\n")
        if in_progress:
            f.write("| Código | Actividad | WBS | % Fís | Fin actual | Fin LB | Retraso |\n"
                    "|--------|-----------|-----|-------|-----------|--------|---------|\n")
            for t in sorted(in_progress, key=lambda x: x.get("early_end", "")):
                lag = "⚠️ SÍ" if t.get("slipped") else "—"
                f.write(f"| {t['code']} | {t['name'][:55]} | {t['wbs'][:30]} | {t['phys_pct']:.0f}% "
                        f"| {t.get('ac_end_cur','?')} | {t.get('bl_end','?')} | {lag} |\n")
        else:
            f.write("_Ninguna_\n")

        f.write("\n---\n\n## ❌ No Iniciadas con Retraso (debían empezar/terminar antes del corte)\n\n")
        if not_started_late:
            f.write("| Código | Actividad | WBS | Fin LB |\n|--------|-----------|-----|--------|\n")
            for t in sorted(not_started_late, key=lambda x: to_dt(x.get("target_end") or x.get("early_end")) or datetime.max):
                bl_e = to_dt(t.get("target_end") or t.get("early_end"))
                f.write(f"| {t['code']} | {t['name'][:60]} | {t['wbs'][:35]} | {bl_e.strftime('%Y-%m-%d') if bl_e else '?'} |\n")
        else:
            f.write("_Ninguna_\n")

        f.write("\n---\n\n## 🏁 Próximos Hitos\n\n")
        if milestones:
            f.write("| Código | Nombre | Fecha est. | Float (h) |\n|--------|--------|-----------|----------|\n")
            for m in milestones[:8]:
                f.write(f"| {m['code']} | {m['name'][:55]} | {m['early_end'][:10]} | {m['float_hr']:.0f} |\n")

        f.write("\n---\n\n_Generado automáticamente por compare_xer.py_\n")

    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
