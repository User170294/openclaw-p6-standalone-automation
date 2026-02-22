import argparse
import csv
import json
from collections import defaultdict
from datetime import datetime
from pathlib import Path


def parse_xer(path: Path):
    tables = {}
    current = None
    fields = []

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
                row = dict(zip(fields, vals))
                tables[current]["rows"].append(row)
    return tables


def to_dt(s):
    if not s:
        return None
    for fmt in ["%Y-%m-%d %H:%M", "%Y-%m-%d %H:%M:%S"]:
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            pass
    return None


def to_float(x, default=None):
    try:
        return float(x)
    except Exception:
        return default


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--xer", required=True)
    ap.add_argument("--project-dir", required=True)
    ap.add_argument("--project-code", required=True)
    args = ap.parse_args()

    xer = Path(args.xer)
    pdir = Path(args.project_dir)
    out_dir = pdir / "docs" / "schedule"
    out_dir.mkdir(parents=True, exist_ok=True)

    tables = parse_xer(xer)
    proj = (tables.get("PROJECT", {}) or {}).get("rows", [{}])[0]
    tasks = (tables.get("TASK", {}) or {}).get("rows", [])
    wbs = (tables.get("PROJWBS", {}) or {}).get("rows", [])

    wbs_map = {r.get("wbs_id"): r.get("wbs_name") or r.get("wbs_short_name") for r in wbs}

    # Task analytics
    enriched = []
    for t in tasks:
        early_start = to_dt(t.get("early_start_date"))
        early_end = to_dt(t.get("early_end_date"))
        target_start = to_dt(t.get("target_start_date"))
        target_end = to_dt(t.get("target_end_date"))
        total_float = to_float(t.get("total_float_hr_cnt"), 0.0)
        remain_hr = to_float(t.get("remain_drtn_hr_cnt"), 0.0)
        phys = to_float(t.get("phys_complete_pct"), 0.0)
        driving = (t.get("driving_path_flag") or "").upper() == "Y"
        enriched.append({
            "task_code": t.get("task_code"),
            "task_name": t.get("task_name"),
            "status": t.get("status_code"),
            "type": t.get("task_type"),
            "wbs": wbs_map.get(t.get("wbs_id"), ""),
            "early_start": t.get("early_start_date"),
            "early_end": t.get("early_end_date"),
            "target_start": t.get("target_start_date"),
            "target_end": t.get("target_end_date"),
            "total_float_hr": total_float,
            "remain_hr": remain_hr,
            "phys_complete_pct": phys,
            "driving_path": driving,
        })

    milestones = [e for e in enriched if e["type"] in {"TT_FinMile", "TT_Mile"}]
    critical = [e for e in enriched if e["total_float_hr"] == 0]
    upcoming_milestones = sorted(
        [m for m in milestones if m["early_end"]], key=lambda x: x["early_end"]
    )[:10]

    proj_name = proj.get("proj_short_name", args.project_code)
    plan_start = proj.get("plan_start_date", "")
    scd_end = proj.get("scd_end_date", "")
    last_sched = proj.get("last_schedule_date", "")

    status_counts = defaultdict(int)
    for e in enriched:
        status_counts[e["status"]] += 1

    summary = {
        "project_code": args.project_code,
        "project_name": proj_name,
        "plan_start": plan_start,
        "scheduled_finish": scd_end,
        "last_schedule_date": last_sched,
        "tasks_total": len(enriched),
        "milestones_total": len(milestones),
        "critical_total_float_zero": len(critical),
        "status_counts": dict(status_counts),
        "source_xer": str(xer),
        "generated_at": datetime.now().isoformat(timespec="seconds"),
    }

    # outputs
    json_path = out_dir / "xer_summary.json"
    md_path = out_dir / "xer_summary.md"
    crit_csv = out_dir / "critical_tasks.csv"

    with json_path.open("w", encoding="utf-8") as f:
        json.dump({"summary": summary, "upcoming_milestones": upcoming_milestones[:8]}, f, ensure_ascii=False, indent=2)

    with crit_csv.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["task_code", "task_name", "status", "type", "wbs", "early_start", "early_end", "total_float_hr", "remain_hr", "driving_path"])
        w.writeheader()
        for e in critical:
            w.writerow({k: e.get(k, "") for k in w.fieldnames})

    with md_path.open("w", encoding="utf-8") as f:
        f.write(f"# Resumen XER — {args.project_code}\n\n")
        f.write(f"- Proyecto (XER): **{proj_name}**\n")
        f.write(f"- Inicio plan: **{plan_start or 'n/d'}**\n")
        f.write(f"- Fin programado: **{scd_end or 'n/d'}**\n")
        f.write(f"- Última programación: **{last_sched or 'n/d'}**\n")
        f.write(f"- Total actividades: **{len(enriched)}**\n")
        f.write(f"- Hitos: **{len(milestones)}**\n")
        f.write(f"- Actividades con float 0h: **{len(critical)}**\n\n")
        f.write("## Estado de actividades\n")
        for k, v in sorted(status_counts.items(), key=lambda kv: kv[0]):
            f.write(f"- {k}: {v}\n")
        f.write("\n## Próximos hitos (top)\n")
        if not upcoming_milestones:
            f.write("- Sin hitos detectados con fecha.\n")
        else:
            for m in upcoming_milestones[:8]:
                f.write(f"- **{m['task_code']}** · {m['task_name']} · {m['early_end']} · float {m['total_float_hr']}h\n")
        f.write("\n## Archivos generados\n")
        f.write("- `xer_summary.json`\n- `xer_summary.md`\n- `critical_tasks.csv`\n")

    print(json.dumps(summary, ensure_ascii=False))


if __name__ == "__main__":
    main()
