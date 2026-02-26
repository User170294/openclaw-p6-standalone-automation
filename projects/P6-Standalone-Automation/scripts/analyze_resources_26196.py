import sqlite3
from pathlib import Path

DB = Path(r"C:\Users\josej\OneDrive\Documentos\PPMDBSQLite_20221109_BBDD_JJC_Rev B - copia_WORK_20260226_145427.db")
PROJ_ID = 26196

con = sqlite3.connect(DB)
con.row_factory = sqlite3.Row
cur = con.cursor()

for t in ["RSRC", "TASKRSRC", "TASK", "PROJECT", "PROJWBS", "NEXTKEY"]:
    cur.execute(f"PRAGMA table_info({t})")
    cols = cur.fetchall()
    print(f"\n--- {t} columns ({len(cols)}) ---")
    for c in cols:
        print(f"{c['name']}|{c['type']}")

print("\n--- Existing resource assignments in project ---")
q = """
SELECT tr.TASKRSRC_ID, tr.TASK_ID, t.TASK_CODE, t.TASK_NAME, tr.RSRC_ID,
       tr.TARGET_QTY, tr.TARGET_COST, tr.REMAIN_QTY, tr.ACT_REG_QTY, tr.ACT_OT_QTY
FROM TASKRSRC tr
JOIN TASK t ON t.TASK_ID = tr.TASK_ID
WHERE t.PROJ_ID = ?
ORDER BY t.TASK_CODE
LIMIT 40
"""
rows = cur.execute(q, (PROJ_ID,)).fetchall()
print(f"ASSIGN_ROWS={len(rows)} (showing up to 40)")
for r in rows:
    act_qty = (r['ACT_REG_QTY'] or 0) + (r['ACT_OT_QTY'] or 0)
    print(f"{r['TASKRSRC_ID']}|{r['TASK_ID']}|{r['TASK_CODE']}|{r['RSRC_ID']}|TGT_QTY={r['TARGET_QTY']}|REM_QTY={r['REMAIN_QTY']}|ACT_QTY={act_qty}")

print("\n--- Distinct resources used in project ---")
q2 = """
SELECT tr.RSRC_ID, COUNT(*) AS n
FROM TASKRSRC tr
JOIN TASK t ON t.TASK_ID = tr.TASK_ID
WHERE t.PROJ_ID = ?
GROUP BY tr.RSRC_ID
ORDER BY n DESC
"""
rows2 = cur.execute(q2, (PROJ_ID,)).fetchall()
for r in rows2:
    print(f"RSRC_ID={r['RSRC_ID']}|ASSIGNMENTS={r['n']}")

print("\n--- Resource names for those RSRC_ID ---")
for r in rows2:
    rr = cur.execute("SELECT RSRC_ID, RSRC_SHORT_NAME, RSRC_NAME FROM RSRC WHERE RSRC_ID=?", (r['RSRC_ID'],)).fetchone()
    if rr:
        print(f"{rr['RSRC_ID']}|{rr['RSRC_SHORT_NAME']}|{rr['RSRC_NAME']}")
