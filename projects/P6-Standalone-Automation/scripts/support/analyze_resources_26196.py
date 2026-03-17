#!/usr/bin/env python3
"""Analiza asignaciones de recursos en un proyecto P6."""

import argparse
import sys
from pathlib import Path

SCRIPTS_ROOT = Path(__file__).resolve().parents[1]
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

from p6_utils import open_db


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--db', required=True, help='Ruta a DB SQLite P6')
    ap.add_argument('--proj-id', type=int, required=True, help='PROJ_ID a inspeccionar')
    ap.add_argument('--limit', type=int, default=40, help='Máximo de asignaciones a mostrar')
    args = ap.parse_args()

    con = open_db(args.db)
    cur = con.cursor()

    print(f'\n--- Existing resource assignments in project {args.proj_id} ---')
    q = """
    SELECT tr.TASKRSRC_ID, tr.TASK_ID, t.TASK_CODE, t.TASK_NAME, tr.RSRC_ID,
           tr.TARGET_QTY, tr.TARGET_COST, tr.REMAIN_QTY, tr.ACT_REG_QTY, tr.ACT_OT_QTY
    FROM TASKRSRC tr
    JOIN TASK t ON t.TASK_ID = tr.TASK_ID
    WHERE t.PROJ_ID = ?
    ORDER BY t.TASK_CODE
    LIMIT ?
    """
    rows = cur.execute(q, (args.proj_id, args.limit)).fetchall()
    print(f'ASSIGN_ROWS={len(rows)} (showing up to {args.limit})')
    for r in rows:
        act_qty = (r['ACT_REG_QTY'] or 0) + (r['ACT_OT_QTY'] or 0)
        print(f"{r['TASKRSRC_ID']}|{r['TASK_ID']}|{r['TASK_CODE']}|{r['RSRC_ID']}|TGT_QTY={r['TARGET_QTY']}|REM_QTY={r['REMAIN_QTY']}|ACT_QTY={act_qty}")

    print('\n--- Distinct resources used in project ---')
    q2 = """
    SELECT tr.RSRC_ID, COUNT(*) AS n
    FROM TASKRSRC tr
    JOIN TASK t ON t.TASK_ID = tr.TASK_ID
    WHERE t.PROJ_ID = ?
    GROUP BY tr.RSRC_ID
    ORDER BY n DESC
    """
    rows2 = cur.execute(q2, (args.proj_id,)).fetchall()
    for r in rows2:
        print(f"RSRC_ID={r['RSRC_ID']}|ASSIGNMENTS={r['n']}")

    print('\n--- Resource names for those RSRC_ID ---')
    for r in rows2:
        rr = cur.execute("SELECT RSRC_ID, RSRC_SHORT_NAME, RSRC_NAME FROM RSRC WHERE RSRC_ID=?", (r['RSRC_ID'],)).fetchone()
        if rr:
            print(f"{rr['RSRC_ID']}|{rr['RSRC_SHORT_NAME']}|{rr['RSRC_NAME']}")

    con.close()


if __name__ == '__main__':
    main()
