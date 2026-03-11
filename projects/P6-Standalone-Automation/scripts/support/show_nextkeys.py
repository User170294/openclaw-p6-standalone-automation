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
    rows = cur.execute('SELECT KEY_NAME, KEY_SEQ_NUM FROM NEXTKEY ORDER BY KEY_NAME').fetchall()
    print(f'COUNT={len(rows)}')
    for r in rows:
        print(f"{r['KEY_NAME']}|{r['KEY_SEQ_NUM']}")
    con.close()


if __name__ == '__main__':
    main()
