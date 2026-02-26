import sqlite3
from pathlib import Path

DB = Path(r"C:\Users\josej\OneDrive\Documentos\PPMDBSQLite_20221109_BBDD_JJC_Rev B - copia_WORK_20260226_145427.db")
PROJ_ID = 26196

con = sqlite3.connect(DB)
con.row_factory = sqlite3.Row
cur = con.cursor()

cur.execute(
    "SELECT COUNT(*) c, COUNT(DISTINCT RSRC_ID) d, "
    "SUM(COALESCE(TARGET_QTY,0)) tq, SUM(COALESCE(REMAIN_QTY,0)) rq "
    "FROM TASKRSRC WHERE PROJ_ID=?",
    (PROJ_ID,),
)
r = cur.fetchone()
print(f"ASSIGNMENTS={r['c']}|DISTINCT_RSRC={r['d']}|SUM_TARGET_QTY={r['tq']}|SUM_REMAIN_QTY={r['rq']}")

print("NEW_RES_SAMPLE")
for x in cur.execute(
    "SELECT RSRC_ID, RSRC_SHORT_NAME, RSRC_NAME FROM RSRC "
    "WHERE RSRC_SHORT_NAME LIKE 'HH-1844-%' ORDER BY RSRC_ID LIMIT 12"
):
    print(f"{x['RSRC_ID']}|{x['RSRC_SHORT_NAME']}|{x['RSRC_NAME']}")

print("OLD_RESOURCE_USAGE")
for x in cur.execute(
    "SELECT RSRC_ID, COUNT(*) c FROM TASKRSRC WHERE PROJ_ID=? AND RSRC_ID IN (9398,9399) GROUP BY RSRC_ID",
    (PROJ_ID,),
):
    print(f"{x['RSRC_ID']}|{x['c']}")
