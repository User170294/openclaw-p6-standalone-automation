import sqlite3

DB = r"C:\Users\josej\OneDrive\Documentos\PPMDBSQLite_20221109_BBDD_JJC_Rev B.db"
ROOT = 151785

con = sqlite3.connect(DB)
cur = con.cursor()

rows = cur.execute(
    """
    SELECT WBS_ID,
           COALESCE(WBS_SHORT_NAME,''),
           COALESCE(WBS_NAME,''),
           COALESCE(PROJ_NODE_FLAG,''),
           COALESCE(PROJ_ID,'')
    FROM PROJWBS
    WHERE PARENT_WBS_ID = ?
    ORDER BY WBS_ID
    """,
    (ROOT,),
).fetchall()

print(f"CHILDREN={len(rows)}")
for r in rows:
    print(f"{r[0]}|{r[1]}|{r[2]}|PROJ_NODE_FLAG={r[3]}|PROJ_ID={r[4]}")

con.close()
