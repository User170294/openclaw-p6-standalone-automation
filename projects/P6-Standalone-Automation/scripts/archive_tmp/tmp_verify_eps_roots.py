import sqlite3

DB = r"C:\Users\josej\OneDrive\Documentos\PPMDBSQLite_20221109_BBDD_JJC_Rev B.db"
con = sqlite3.connect(DB)
cur = con.cursor()

roots = cur.execute(
    """
    SELECT WBS_ID, COALESCE(WBS_SHORT_NAME,''), COALESCE(WBS_NAME,'')
    FROM PROJWBS
    WHERE PARENT_WBS_ID IS NULL
    ORDER BY WBS_ID
    """
).fetchall()

print(f"DB={DB}")
print(f"ROOT_COUNT={len(roots)}")
for wbs_id, short, name in roots:
    print(f"ROOT|{wbs_id}|{short}|{name}")

# sanity: total rows in key tables
for t in ("PROJECT", "PROJWBS", "TASK"):
    c = cur.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
    print(f"COUNT_{t}={c}")

con.close()
