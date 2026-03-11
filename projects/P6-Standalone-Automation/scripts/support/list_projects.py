import argparse
import sqlite3
from pathlib import Path


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--db", required=True)
    p.add_argument("--like", default="SIMTEXX")
    args = p.parse_args()

    db = Path(args.db)
    con = sqlite3.connect(db)
    con.row_factory = sqlite3.Row
    cur = con.cursor()

    cur.execute("PRAGMA table_info(PROJECT)")
    cols = [r[1] for r in cur.fetchall()]

    text_cols = [c for c in ["PROJ_SHORT_NAME", "PROJ_NAME", "GUID", "CREATE_USER", "UPDATE_USER"] if c in cols]

    like = f"%{args.like.upper()}%"

    if "PROJ_SHORT_NAME" in cols and "PROJ_NAME" in cols:
        q = """
        SELECT PROJ_ID, PROJ_SHORT_NAME, PROJ_NAME
        FROM PROJECT
        WHERE UPPER(COALESCE(PROJ_SHORT_NAME,'')) LIKE ?
           OR UPPER(COALESCE(PROJ_NAME,'')) LIKE ?
        ORDER BY PROJ_SHORT_NAME
        """
        rows = cur.execute(q, (like, like)).fetchall()
        print(f"MATCHES={len(rows)}")
        for r in rows:
            print(f"{r['PROJ_ID']}|{r['PROJ_SHORT_NAME']}|{r['PROJ_NAME']}")
    elif "PROJ_SHORT_NAME" in cols:
        q = """
        SELECT PROJ_ID, PROJ_SHORT_NAME
        FROM PROJECT
        WHERE UPPER(COALESCE(PROJ_SHORT_NAME,'')) LIKE ?
        ORDER BY PROJ_SHORT_NAME
        """
        rows = cur.execute(q, (like,)).fetchall()
        print(f"MATCHES={len(rows)}")
        for r in rows:
            print(f"{r['PROJ_ID']}|{r['PROJ_SHORT_NAME']}")
    else:
        print("PROJECT columns:")
        for c in cols:
            print(c)


if __name__ == "__main__":
    main()
