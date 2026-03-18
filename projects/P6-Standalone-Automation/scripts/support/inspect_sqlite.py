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
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    tables = [r[0] for r in cur.fetchall()]
    print(f'TABLE_COUNT={len(tables)}')
    for name in tables[:40]:
        print(name)

    print('\n--- TASK columns ---')
    cur.execute('PRAGMA table_info(TASK)')
    for col in cur.fetchall():
        print(f"{col[1]}|{col[2]}")

    print('\n--- TASKPRED columns ---')
    cur.execute('PRAGMA table_info(TASKPRED)')
    for col in cur.fetchall():
        print(f"{col[1]}|{col[2]}")

    print('\n--- PROJWBS columns ---')
    cur.execute('PRAGMA table_info(PROJWBS)')
    for col in cur.fetchall():
        print(f"{col[1]}|{col[2]}")

    print('\n--- PROJWBS like SIMTEXX ---')
    cur.execute("""
    SELECT WBS_ID, PROJ_ID, WBS_SHORT_NAME, WBS_NAME, PARENT_WBS_ID
    FROM PROJWBS
    WHERE UPPER(COALESCE(WBS_SHORT_NAME,'')) LIKE '%SIMTEXX%'
       OR UPPER(COALESCE(WBS_NAME,'')) LIKE '%SIMTEXX%'
    ORDER BY PROJ_ID, WBS_ID
    LIMIT 30
    """)
    for row in cur.fetchall():
        print('|'.join([str(x) if x is not None else '' for x in row]))
    con.close()


if __name__ == '__main__':
    main()
