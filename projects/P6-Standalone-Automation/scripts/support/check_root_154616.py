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
    ap.add_argument('--wbs-id', type=int, default=154616)
    ap.add_argument('--proj-id', type=int, default=26260)
    args = ap.parse_args()

    con = open_db(args.db)
    cur = con.cursor()
    print(cur.execute('select WBS_ID, WBS_SHORT_NAME, WBS_NAME, PROJ_ID, PARENT_WBS_ID from PROJWBS where WBS_ID=?', (args.wbs_id,)).fetchall())
    print(cur.execute('select PROJ_ID, PROJ_SHORT_NAME from PROJECT where PROJ_ID=?', (args.proj_id,)).fetchall())
    con.close()


if __name__ == '__main__':
    main()
