import argparse
import csv
import sqlite3
from datetime import datetime
from pathlib import Path


def parse_args():
    p = argparse.ArgumentParser(description="Pilot audit for Primavera P6 Standalone SQLite")
    p.add_argument("--db", required=True, help="Path to PPMDBSQLite .db")
    p.add_argument("--out-dir", default="projects/P6-Standalone-Automation/data", help="Output folder")
    p.add_argument("--proj-id", type=int, default=None, help="Optional PROJ_ID filter")
    p.add_argument("--dry-run", action="store_true", help="No write-back actions (default behavior)")
    return p.parse_args()


def main():
    args = parse_args()
    db_path = Path(args.db)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    now = datetime.now()
    stamp = now.strftime("%Y%m%d_%H%M%S")

    con = sqlite3.connect(db_path)
    con.row_factory = sqlite3.Row
    cur = con.cursor()

    where_proj = ""
    params = []
    if args.proj_id is not None:
        where_proj = " AND t.PROJ_ID = ?"
        params.append(args.proj_id)

    q_no_pred = f"""
    SELECT t.PROJ_ID, t.TASK_ID, t.TASK_CODE, t.TASK_NAME, t.STATUS_CODE, t.TASK_TYPE, t.TARGET_END_DATE
    FROM TASK t
    LEFT JOIN TASKPRED tp ON tp.TASK_ID = t.TASK_ID
    WHERE tp.TASK_ID IS NULL
      AND (t.STATUS_CODE IS NULL OR t.STATUS_CODE <> 'TK_Complete')
      {where_proj}
    ORDER BY t.PROJ_ID, t.TASK_CODE
    """

    q_overdue_miles = f"""
    SELECT t.PROJ_ID, t.TASK_ID, t.TASK_CODE, t.TASK_NAME, t.STATUS_CODE, t.TASK_TYPE, t.TARGET_END_DATE
    FROM TASK t
    WHERE t.TASK_TYPE IN ('TT_Mile', 'TT_FinMile', 'TT_LOE')
      AND t.TARGET_END_DATE IS NOT NULL
      AND datetime(t.TARGET_END_DATE) < datetime('now','localtime')
      AND (t.STATUS_CODE IS NULL OR t.STATUS_CODE <> 'TK_Complete')
      {where_proj}
    ORDER BY t.PROJ_ID, t.TARGET_END_DATE
    """

    no_pred = cur.execute(q_no_pred, params).fetchall()
    overdue = cur.execute(q_overdue_miles, params).fetchall()

    csv_path = out_dir / f"pilot_audit_{stamp}.csv"
    md_path = out_dir / f"pilot_audit_{stamp}.md"

    fields = ["check", "PROJ_ID", "TASK_ID", "TASK_CODE", "TASK_NAME", "STATUS_CODE", "TASK_TYPE", "TARGET_END_DATE"]

    with csv_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for row in no_pred:
            w.writerow({"check": "NO_PREDECESSOR", **dict(row)})
        for row in overdue:
            w.writerow({"check": "OVERDUE_MILESTONE", **dict(row)})

    with md_path.open("w", encoding="utf-8") as f:
        f.write(f"# Pilot Audit P6 Standalone ({stamp})\n\n")
        f.write(f"- DB: `{db_path}`\n")
        f.write(f"- PROJ_ID filtro: `{args.proj_id}`\n")
        f.write(f"- Dry-run: `{True}`\n\n")
        f.write("## Resumen\n")
        f.write(f"- Actividades sin predecesora: **{len(no_pred)}**\n")
        f.write(f"- Hitos/actividades tipo milestone vencidos: **{len(overdue)}**\n\n")
        f.write(f"Detalle completo: `{csv_path}`\n")

    print(f"OK CSV={csv_path}")
    print(f"OK MD={md_path}")
    print(f"NO_PREDECESSOR={len(no_pred)}")
    print(f"OVERDUE_MILESTONE={len(overdue)}")


if __name__ == "__main__":
    main()
