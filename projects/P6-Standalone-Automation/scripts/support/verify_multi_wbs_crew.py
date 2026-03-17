import argparse
from pathlib import Path
import sys

SCRIPTS_ROOT = Path(__file__).resolve().parents[1]
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

from p6_utils import open_db


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--db', required=True)
    ap.add_argument('--proj-id', type=int, default=None)
    ap.add_argument('--wbs-list', nargs='+', type=int, default=[153937, 153962, 153970, 153978, 153986])
    args = ap.parse_args()

    con = open_db(args.db)
    cur = con.cursor()
    for wbs_id in args.wbs_list:
        q = '''
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
        '''
        r = cur.execute(q, (args.proj_id, wbs_id, args.proj_id, args.proj_id)).fetchone()
        print(f"WBS={wbs_id}|ROWS={r['rows']}|DISTINCT_RSRC={r['distinct_rsrc']}|TARGET={r['sum_target']}|REMAIN={r['sum_remain']}")
        for x in cur.execute('SELECT RSRC_ID,RSRC_SHORT_NAME FROM RSRC WHERE RSRC_SHORT_NAME LIKE ? ORDER BY RSRC_ID', (f'W{wbs_id}-%',)):
            print(f"  {x['RSRC_ID']}|{x['RSRC_SHORT_NAME']}")
    con.close()


if __name__ == '__main__':
    main()
