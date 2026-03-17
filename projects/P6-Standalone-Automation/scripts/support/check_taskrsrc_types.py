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
    ap.add_argument('--min-rsrc-id', type=int, default=9555)
    ap.add_argument('--max-rsrc-id', type=int, default=9569)
    args = ap.parse_args()

    con = open_db(args.db)
    cur = con.cursor()
    q = '''
    select RSRC_TYPE, count(*)
    from TASKRSRC
    where PROJ_ID=? and RSRC_ID between ? and ?
    group by RSRC_TYPE
    '''
    for r in cur.execute(q, (args.proj_id, args.min_rsrc_id, args.max_rsrc_id)):
        print('|'.join(str(x) for x in r))
    con.close()


if __name__ == '__main__':
    main()
