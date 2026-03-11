import argparse
from pathlib import Path
import sys

SCRIPTS_ROOT = Path(__file__).resolve().parents[1]
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

from p6_utils import open_db


def fetch_ids(cur, keep_root):
    root_rows = cur.execute(
        "SELECT WBS_ID FROM PROJWBS WHERE PARENT_WBS_ID IS NULL"
    ).fetchall()
    root_ids = [r[0] for r in root_rows]
    del_roots = [r for r in root_ids if r != keep_root]

    # All WBS to delete (all descendants of roots to delete)
    del_wbs = set()
    del_proj = set()

    cte = """
    WITH RECURSIVE t AS (
      SELECT WBS_ID, PROJ_ID FROM PROJWBS WHERE WBS_ID = ?
      UNION ALL
      SELECT c.WBS_ID, c.PROJ_ID
      FROM PROJWBS c
      JOIN t p ON c.PARENT_WBS_ID = p.WBS_ID
    )
    SELECT WBS_ID, PROJ_ID FROM t
    """

    for root in del_roots:
        for wbs_id, proj_id in cur.execute(cte, (root,)).fetchall():
            del_wbs.add(wbs_id)
            if proj_id is not None:
                del_proj.add(proj_id)

    return root_ids, del_roots, del_wbs, del_proj


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", required=True)
    ap.add_argument("--keep-root", type=int, required=True)
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    db = Path(args.db)
    con = open_db(db)
    cur = con.cursor()

    root_ids, del_roots, del_wbs, del_proj = fetch_ids(cur, args.keep_root)

    print(f"ROOTS_TOTAL={len(root_ids)}")
    print(f"ROOTS_TO_DELETE={len(del_roots)}")
    print(f"WBS_TO_DELETE={len(del_wbs)}")
    print(f"PROJECTS_TO_DELETE={len(del_proj)}")

    if not args.apply:
        print("MODE=PLAN")
        con.close()
        return

    # Best-effort dependent cleanup by PROJ_ID
    proj_tables = [
        "TASKRSRC",
        "TASKPRED",
        "TASK",
        "TASKSUM",
        "TASKSUMFIN",
        "TRSRCSUM",
        "TRSRCSUMFN",
        "WBSBUDG",
        "WBSMEMO",
        "WBSRSRC",
        "WBSSTEP",
    ]
    existing_tables = {
        r[0]
        for r in cur.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
    }
    proj_tables = [t for t in proj_tables if t in existing_tables]

    deleted = {}
    try:
        con.execute("BEGIN")
        def delete_in_chunks(table, col, ids, chunk=900):
            ids = list(ids)
            total = 0
            for i in range(0, len(ids), chunk):
                part = ids[i:i+chunk]
                marks = ",".join(["?"] * len(part))
                cur.execute(f"DELETE FROM {table} WHERE {col} IN ({marks})", tuple(part))
                total += cur.rowcount
            return total

        if del_proj:
            for t in proj_tables:
                deleted[t] = delete_in_chunks(t, "PROJ_ID", del_proj)

        if del_wbs:
            deleted["PROJWBS"] = delete_in_chunks("PROJWBS", "WBS_ID", del_wbs)

        if del_proj:
            deleted["PROJECT"] = delete_in_chunks("PROJECT", "PROJ_ID", del_proj)

        con.commit()
    except Exception:
        con.rollback()
        raise
    finally:
        # verify roots left
        left = cur.execute(
            "SELECT WBS_ID, WBS_SHORT_NAME, WBS_NAME FROM PROJWBS WHERE PARENT_WBS_ID IS NULL ORDER BY WBS_ID"
        ).fetchall()
        print("MODE=APPLY")
        for k in sorted(deleted):
            print(f"DELETED_{k}={deleted[k]}")
        print(f"ROOTS_LEFT={len(left)}")
        for r in left:
            print(f"ROOT|{r[0]}|{r[1] or ''}|{r[2] or ''}")
        con.close()


if __name__ == "__main__":
    main()
