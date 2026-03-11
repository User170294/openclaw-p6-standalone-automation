import sqlite3
DB = r"C:\Users\josej\OneDrive\Documentos\PPMDBSQLite_20221109_BBDD_JJC_Rev B.db"
con = sqlite3.connect(DB)
con.row_factory = sqlite3.Row
cur = con.cursor()
rows = cur.execute("SELECT TASKRSRC_ID, TASK_ID, RSRC_ID, TARGET_QTY, TARGET_QTY_PER_HR, TARGET_START_DATE, TARGET_END_DATE, TARGET_CRV FROM TASKRSRC WHERE PROJ_ID=26258 AND TARGET_CRV IS NOT NULL AND LENGTH(TRIM(TARGET_CRV))>0 LIMIT 5").fetchall()
print(f"ROWS={len(rows)}")
for r in rows:
    print('---')
    for k in r.keys():
        v=r[k]
        if k=='TARGET_CRV' and v is not None:
            print(f"{k}={str(v)[:200]}")
        else:
            print(f"{k}={v}")
con.close()
