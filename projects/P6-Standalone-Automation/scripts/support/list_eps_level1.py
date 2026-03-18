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
    args = ap.parse_args()

    con = open_db(args.db)
    cur = con.cursor()
    q = '''
    SELECT WBS_ID, COALESCE(WBS_SHORT_NAME,''), COALESCE(WBS_NAME,''), COALESCE(PROJ_ID,''), COALESCE(PARENT_WBS_ID,'')
    FROM PROJWBS
    WHERE PARENT_WBS_ID IS NULL
    ORDER BY WBS_ID
    '''
    rows = cur.execute(q).fetchall()
    print(f'ROOT_COUNT={len(rows)}')
    for r in rows:
        print('|'.join(str(x) for x in r))

    if rows:
        root_id = rows[0][0]
        q2 = '''
        SELECT WBS_ID, COALESCE(WBS_SHORT_NAME,''), COALESCE(WBS_NAME,''), COALESCE(PROJ_ID,''), COALESCE(PARENT_WBS_ID,'')
        FROM PROJWBS
        WHERE PARENT_WBS_ID = ?
        ORDER BY WBS_ID
        '''
        c = cur.execute(q2, (root_id,)).fetchall()
        print(f'LEVEL1_UNDER_{root_id}={len(c)}')
        for r in c:
            print('|'.join(str(x) for x in r))
    con.close()


if __name__ == '__main__':
    main()
