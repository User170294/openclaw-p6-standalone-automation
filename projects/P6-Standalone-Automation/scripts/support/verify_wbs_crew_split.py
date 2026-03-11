import sqlite3
from pathlib import Path

DB=Path(r"C:\Users\josej\OneDrive\Documentos\PPMDBSQLite_20221109_BBDD_JJC_Rev B - copia_WORK_20260226_145427.db")
PROJ_ID=26196
WBS_ID=153937

con=sqlite3.connect(DB)
con.row_factory=sqlite3.Row
cur=con.cursor()

q_tree="""
WITH RECURSIVE wbs_tree AS (
  SELECT WBS_ID FROM PROJWBS WHERE PROJ_ID=? AND WBS_ID=?
  UNION ALL
  SELECT c.WBS_ID
  FROM PROJWBS c
  JOIN wbs_tree p ON c.PARENT_WBS_ID=p.WBS_ID
  WHERE c.PROJ_ID=?
)
SELECT WBS_ID FROM wbs_tree
"""

wbs_ids=[r['WBS_ID'] for r in cur.execute(q_tree,(PROJ_ID,WBS_ID,PROJ_ID)).fetchall()]

q_sum="""
WITH RECURSIVE wbs_tree AS (
  SELECT WBS_ID FROM PROJWBS WHERE PROJ_ID=? AND WBS_ID=?
  UNION ALL
  SELECT c.WBS_ID
  FROM PROJWBS c
  JOIN wbs_tree p ON c.PARENT_WBS_ID=p.WBS_ID
  WHERE c.PROJ_ID=?
)
SELECT COUNT(*) as rows,
       COUNT(DISTINCT tr.RSRC_ID) as distinct_rsrc,
       SUM(COALESCE(tr.TARGET_QTY,0)) as sum_target,
       SUM(COALESCE(tr.REMAIN_QTY,0)) as sum_remain
FROM TASKRSRC tr
JOIN TASK t ON t.TASK_ID=tr.TASK_ID
WHERE t.PROJ_ID=? AND t.WBS_ID IN (SELECT WBS_ID FROM wbs_tree)
"""

r=cur.execute(q_sum,(PROJ_ID,WBS_ID,PROJ_ID,PROJ_ID)).fetchone()
print(f"WBS_TREE_NODES={len(wbs_ids)}")
print(f"ASSIGN_ROWS={r['rows']}|DISTINCT_RSRC={r['distinct_rsrc']}|SUM_TARGET={r['sum_target']}|SUM_REMAIN={r['sum_remain']}")

print('CREW_RESOURCES')
for x in cur.execute("SELECT RSRC_ID, RSRC_SHORT_NAME, RSRC_NAME FROM RSRC WHERE RSRC_SHORT_NAME LIKE ? ORDER BY RSRC_ID", (f"W{WBS_ID}-%",)):
    print(f"{x['RSRC_ID']}|{x['RSRC_SHORT_NAME']}|{x['RSRC_NAME']}")
