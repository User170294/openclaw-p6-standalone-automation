import argparse
from pathlib import Path
import sys

SCRIPTS_ROOT = Path(__file__).resolve().parents[1]
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

from p6_utils import open_db


def descendants_by_root(cur, root_wbs_id):
    q = """
    WITH RECURSIVE t AS (
      SELECT WBS_ID, PROJ_ID FROM PROJWBS WHERE WBS_ID = ?
      UNION ALL
      SELECT c.WBS_ID, c.PROJ_ID
      FROM PROJWBS c
      JOIN t p ON c.PARENT_WBS_ID = p.WBS_ID
    )
    SELECT WBS_ID, PROJ_ID FROM t
    """
    return cur.execute(q, (root_wbs_id,)).fetchall()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", required=True)
    ap.add_argument("--root", type=int, required=True)
    ap.add_argument("--keep-proj", required=True, help="CSV proj_ids a mantener")
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    keep_proj = {int(x.strip()) for x in args.keep_proj.split(",") if x.strip()}

    con = open_db(Path(args.db))
    cur = con.cursor()

    rows = descendants_by_root(cur, args.root)
    all_wbs = {r[0] for r in rows}
    all_proj = {r[1] for r in rows if r[1] is not None}

    del_proj = sorted([p for p in all_proj if p not in keep_proj])
    keep_wbs = {
        w for (w, p) in rows if (p is None or p in keep_proj)
    }
    del_wbs = sorted([w for w in all_wbs if w not in keep_wbs and w != args.root])

    print(f"ROOT={args.root}")
    print(f"PROJECTS_ALL={len(all_proj)}")
    print(f"PROJECTS_KEEP={len(keep_proj)}")
    print(f"PROJECTS_DELETE={len(del_proj)}")
    print(f"WBS_DELETE={len(del_wbs)}")

    if not args.apply:
        print("MODE=PLAN")
        con.close()
        return

    def delete_in_chunks(table, col, ids, chunk=900):
        ids = list(ids)
        total = 0
        for i in range(0, len(ids), chunk):
            part = ids[i:i+chunk]
            marks = ",".join(["?"] * len(part))
            cur.execute(f"DELETE FROM {table} WHERE {col} IN ({marks})", tuple(part))
            total += cur.rowcount
        return total

    proj_tables = ["TASKRSRC", "TASKPRED", "TASK", "WBSBUDG", "WBSMEMO", "WBSRSRC", "WBSSTEP"]
    existing_tables = {r[0] for r in cur.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
    proj_tables = [t for t in proj_tables if t in existing_tables]

    deleted = {}
    try:
        con.execute("BEGIN")
        for t in proj_tables:
            deleted[t] = delete_in_chunks(t, "PROJ_ID", del_proj)
        deleted["PROJECT"] = delete_in_chunks("PROJECT", "PROJ_ID", del_proj)
        deleted["PROJWBS"] = delete_in_chunks("PROJWBS", "WBS_ID", del_wbs)
        con.commit()
    except Exception:
        con.rollback()
        raise

    left = cur.execute(
        "SELECT PROJ_ID, PROJ_SHORT_NAME FROM PROJECT WHERE PROJ_ID IN (26196,26197,26198,26257,26258) ORDER BY PROJ_ID"
    ).fetchall()
    left_all = cur.execute(
        "SELECT COUNT(*) FROM PROJECT WHERE PROJ_ID IN (SELECT DISTINCT PROJ_ID FROM PROJWBS WHERE WBS_ID IN (SELECT WBS_ID FROM PROJWBS WHERE PARENT_WBS_ID=? OR WBS_ID=?))",
        (args.root, args.root)
    ).fetchone()[0]

    print("MODE=APPLY")
    for k in sorted(deleted):
        print(f"DELETED_{k}={deleted[k]}")
    print(f"LEFT_KEEP_MATCH={len(left)}")
    for r in left:
        print(f"KEEP|{r[0]}|{r[1]}")
    print(f"ROOT_DIRECT_PROJECT_COUNT={left_all}")
    con.close()


if __name__ == "__main__":
    main()
