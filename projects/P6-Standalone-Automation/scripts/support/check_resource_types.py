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
    ap.add_argument('--pattern', default='W153%OP%')
    ap.add_argument('--rsrc-ids', nargs='*', type=int, default=[9398, 9399])
    args = ap.parse_args()

    con = open_db(args.db)
    cur = con.cursor()
    marks = ','.join(['?'] * len(args.rsrc_ids))
    q = f"""
    select RSRC_ID, RSRC_SHORT_NAME, RSRC_NAME, coalesce(RSRC_TYPE,''), coalesce(UNIT_ID,'')
    from RSRC
    where RSRC_SHORT_NAME like ? or RSRC_ID in ({marks})
    order by RSRC_ID
    """
    for r in cur.execute(q, [args.pattern, *args.rsrc_ids]):
        print('|'.join(str(x) for x in r))
    con.close()


if __name__ == '__main__':
    main()
