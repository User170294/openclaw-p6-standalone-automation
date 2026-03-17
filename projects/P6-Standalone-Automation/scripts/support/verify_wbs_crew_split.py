#!/usr/bin/env python3
"""Verifica el split de recursos por WBS/cuadrilla en un proyecto P6."""

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
    ap.add_argument('--wbs-id', type=int, required=True, help='WBS_ID raíz a verificar')
    args = ap.parse_args()

    con = open_db(args.db)
    cur = con.cursor()

    q_tree = """
    WITH RECURSIVE wbs_tree AS (
      SELECT WBS_ID FROM PROJWBS WHERE PROJ_ID=? AND WBS_ID=?
      UNION ALL
      SELECT c.WBS_ID
      FROM PROJWBS c
      JOIN wbs_tree p ON c.PARENT_WBS_ID=p.WBS_ID
      WHERE c.PROJ_ID=?
    )
    SELECT WBS_ID FROM wbs_tree
    """

    wbs_ids = [r['WBS_ID'] for r in cur.execute(q_tree, (args.proj_id, args.wbs_id, args.proj_id)).fetchall()]

    q_sum = """
    WITH RECURSIVE wbs_tree AS (
      SELECT WBS_ID FROM PROJWBS WHERE PROJ_ID=? AND WBS_ID=?
      UNION ALL
      SELECT c.WBS_ID
      FROM PROJWBS c
      JOIN wbs_tree p ON c.PARENT_WBS_ID=p.WBS_ID
      WHERE c.PROJ_ID=?
    )
    SELECT COUNT(*) as rows,
           COUNT(DISTINCT tr.RSRC_ID) as distinct_rsrc,
           SUM(COALESCE(tr.TARGET_QTY,0)) as sum_target,
           SUM(COALESCE(tr.REMAIN_QTY,0)) as sum_remain
    FROM TASKRSRC tr
    JOIN TASK t ON t.TASK_ID=tr.TASK_ID
    WHERE t.PROJ_ID=? AND t.WBS_ID IN (SELECT WBS_ID FROM wbs_tree)
    """

    r = cur.execute(q_sum, (args.proj_id, args.wbs_id, args.proj_id, args.proj_id)).fetchone()
    print(f"WBS_TREE_NODES={len(wbs_ids)}")
    print(f"ASSIGN_ROWS={r['rows']}|DISTINCT_RSRC={r['distinct_rsrc']}|SUM_TARGET={r['sum_target']}|SUM_REMAIN={r['sum_remain']}")

    print('CREW_RESOURCES')
    for x in cur.execute("SELECT RSRC_ID, RSRC_SHORT_NAME, RSRC_NAME FROM RSRC WHERE RSRC_SHORT_NAME LIKE ? ORDER BY RSRC_ID", (f"W{args.wbs_id}-%",)):
        print(f"{x['RSRC_ID']}|{x['RSRC_SHORT_NAME']}|{x['RSRC_NAME']}")

    con.close()


if __name__ == '__main__':
    main()
