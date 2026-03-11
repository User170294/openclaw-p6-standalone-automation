import sqlite3

DB = r"C:\Users\josej\OneDrive\Documentos\PPMDBSQLite_20221109_BBDD_JJC_Rev B.db"
ROOT_ID = 151785

con = sqlite3.connect(DB)
cur = con.cursor()
rows = cur.execute(
    """
    SELECT WBS_ID, COALESCE(WBS_SHORT_NAME,''), COALESCE(WBS_NAME,'')
    FROM PROJWBS
    WHERE PARENT_WBS_ID = ?
    ORDER BY WBS_ID
    """,
    (ROOT_ID,),
).fetchall()

print(f"COUNT={len(rows)}")
for r in rows:
    print(f"{r[0]}|{r[1]}|{r[2]}")

con.close()
