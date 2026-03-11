import sqlite3

DB = r"C:\Users\josej\OneDrive\Documentos\PPMDBSQLite_20221109_BBDD_JJC_Rev B - copia_WORK_20260226_145427.db"
con = sqlite3.connect(DB)
cur = con.cursor()

q = """
SELECT WBS_ID, COALESCE(WBS_SHORT_NAME,''), COALESCE(WBS_NAME,''), COALESCE(PROJ_ID,''), COALESCE(PARENT_WBS_ID,'')
FROM PROJWBS
WHERE PARENT_WBS_ID IS NULL
ORDER BY WBS_ID
"""
rows = cur.execute(q).fetchall()
print(f"ROOT_COUNT={len(rows)}")
for r in rows:
    print("|".join(str(x) for x in r))

if rows:
    root_id = rows[0][0]
    q2 = """
    SELECT WBS_ID, COALESCE(WBS_SHORT_NAME,''), COALESCE(WBS_NAME,''), COALESCE(PROJ_ID,''), COALESCE(PARENT_WBS_ID,'')
    FROM PROJWBS
    WHERE PARENT_WBS_ID = ?
    ORDER BY WBS_ID
    """
    c = cur.execute(q2, (root_id,)).fetchall()
    print(f"LEVEL1_UNDER_{root_id}={len(c)}")
    for r in c:
        print("|".join(str(x) for x in r))

con.close()
