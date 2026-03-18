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
    ap.add_argument('--root', type=int, default=151785)
    ap.add_argument('--targets', nargs='+', type=int, default=[])
    args = ap.parse_args()

    con = open_db(args.db)
    cur = con.cursor()
    marks = ','.join(['?'] * len(args.targets))
    q = f"""
    WITH RECURSIVE t AS (
      SELECT WBS_ID, PROJ_ID, PARENT_WBS_ID FROM PROJWBS WHERE WBS_ID = ?
      UNION ALL
      SELECT c.WBS_ID, c.PROJ_ID, c.PARENT_WBS_ID
      FROM PROJWBS c
      JOIN t p ON c.PARENT_WBS_ID = p.WBS_ID
    )
    SELECT p.PROJ_ID, p.PROJ_SHORT_NAME, MIN(CASE WHEN t.PROJ_ID IS NOT NULL THEN 1 ELSE 0 END) as under_root
    FROM PROJECT p
    LEFT JOIN t ON t.PROJ_ID = p.PROJ_ID
    WHERE p.PROJ_ID IN (" + marks + ")
    GROUP BY p.PROJ_ID, p.PROJ_SHORT_NAME
    ORDER BY p.PROJ_ID
    """
    rows = cur.execute(q, [args.root, *args.targets]).fetchall()
    for r in rows:
        print(f"{r[0]}|{r[1]}|UNDER_ROOT={r[2]}")
    con.close()


if __name__ == '__main__':
    main()
