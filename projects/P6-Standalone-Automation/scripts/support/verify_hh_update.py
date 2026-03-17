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
    ap.add_argument('--sample-pattern', default='HH-1844-%')
    ap.add_argument('--old-rsrc-ids', nargs='*', type=int, default=[9398, 9399])
    args = ap.parse_args()

    con = open_db(args.db)
    cur = con.cursor()
    cur.execute(
        'SELECT COUNT(*) c, COUNT(DISTINCT RSRC_ID) d, SUM(COALESCE(TARGET_QTY,0)) tq, SUM(COALESCE(REMAIN_QTY,0)) rq FROM TASKRSRC WHERE PROJ_ID=?',
        (args.proj_id,),
    )
    r = cur.fetchone()
    print(f"ASSIGNMENTS={r['c']}|DISTINCT_RSRC={r['d']}|SUM_TARGET_QTY={r['tq']}|SUM_REMAIN_QTY={r['rq']}")
    print('NEW_RES_SAMPLE')
    for x in cur.execute('SELECT RSRC_ID, RSRC_SHORT_NAME, RSRC_NAME FROM RSRC WHERE RSRC_SHORT_NAME LIKE ? ORDER BY RSRC_ID LIMIT 12', (args.sample_pattern,)):
        print(f"{x['RSRC_ID']}|{x['RSRC_SHORT_NAME']}|{x['RSRC_NAME']}")
    print('OLD_RESOURCE_USAGE')
    marks = ','.join(['?'] * len(args.old_rsrc_ids))
    for x in cur.execute(f'SELECT RSRC_ID, COUNT(*) c FROM TASKRSRC WHERE PROJ_ID=? AND RSRC_ID IN ({marks}) GROUP BY RSRC_ID', [args.proj_id, *args.old_rsrc_ids]):
        print(f"{x['RSRC_ID']}|{x['c']}")
    con.close()


if __name__ == '__main__':
    main()
