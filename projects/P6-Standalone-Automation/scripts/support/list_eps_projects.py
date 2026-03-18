import argparse
import sqlite3
from pathlib import Path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", required=True)
    ap.add_argument("--eps-wbs-id", type=int, required=True)
    args = ap.parse_args()

    con = sqlite3.connect(Path(args.db))
    con.row_factory = sqlite3.Row
    cur = con.cursor()

    # Recursive CTE: all WBS descendants from EPS root
    q = """
    WITH RECURSIVE wbs_tree AS (
      SELECT WBS_ID, PROJ_ID, WBS_SHORT_NAME, WBS_NAME, PARENT_WBS_ID, 0 AS lvl
      FROM PROJWBS
      WHERE WBS_ID = ?
      UNION ALL
      SELECT c.WBS_ID, c.PROJ_ID, c.WBS_SHORT_NAME, c.WBS_NAME, c.PARENT_WBS_ID, p.lvl + 1
      FROM PROJWBS c
      JOIN wbs_tree p ON c.PARENT_WBS_ID = p.WBS_ID
    )
    SELECT DISTINCT t.PROJ_ID, p.PROJ_SHORT_NAME, t.WBS_ID, t.WBS_SHORT_NAME, t.WBS_NAME, t.lvl
    FROM wbs_tree t
    LEFT JOIN PROJECT p ON p.PROJ_ID = t.PROJ_ID
    ORDER BY t.lvl, t.WBS_ID;
    """

    rows = cur.execute(q, (args.eps_wbs_id,)).fetchall()
    print(f"COUNT={len(rows)}")
    for r in rows:
      print(f"{r['PROJ_ID']}|{r['PROJ_SHORT_NAME'] or ''}|{r['WBS_ID']}|{r['WBS_SHORT_NAME'] or ''}|{r['WBS_NAME'] or ''}|L{r['lvl']}")


if __name__ == "__main__":
    main()
