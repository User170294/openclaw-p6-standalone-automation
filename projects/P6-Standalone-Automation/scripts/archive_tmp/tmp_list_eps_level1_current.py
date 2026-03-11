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

print(f"ROOT_COUNT={len(roots)}")
for r in roots:
    print(f"{r[0]}|{r[1]}|{r[2]}")

if roots:
    root_id = roots[0][0]
    level1 = cur.execute(
        """
        SELECT WBS_ID, COALESCE(WBS_SHORT_NAME,''), COALESCE(WBS_NAME,'')
        FROM PROJWBS
        WHERE PARENT_WBS_ID = ?
        ORDER BY WBS_ID
        """,
        (root_id,),
    ).fetchall()
    print(f"LEVEL1_UNDER_{root_id}={len(level1)}")
    for r in level1:
        print(f"{r[0]}|{r[1]}|{r[2]}")

con.close()
