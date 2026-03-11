import sqlite3
from datetime import date

DB=r"C:\Users\josej\OneDrive\Documentos\PPMDBSQLite_20221109_BBDD_JJC_Rev B.db"
PROJ=26262
WS='2026-02-23'
WE='2026-03-01'

con=sqlite3.connect(DB)
con.row_factory=sqlite3.Row
cur=con.cursor()

# snapshot totals
r=cur.execute('''
SELECT
  SUM(COALESCE(ACT_REG_QTY,0)) act_qty,
  SUM(COALESCE(REMAIN_QTY,0)) rem_qty,
  SUM(COALESCE(TARGET_QTY,0)) tgt_qty,
  SUM(COALESCE(ACT_REG_COST,0)+COALESCE(ACT_OT_COST,0)) act_cost,
  SUM(COALESCE(REMAIN_COST,0)) rem_cost,
  SUM(COALESCE(TARGET_COST,0)) tgt_cost
FROM TASKRSRC WHERE PROJ_ID=?
''',(PROJ,)).fetchone()
print('SNAPSHOT',dict(r))

# week by target end in week
r2=cur.execute('''
SELECT
  SUM(COALESCE(REMAIN_COST,0)) rem_cost,
  SUM(COALESCE(TARGET_COST,0)) tgt_cost,
  SUM(COALESCE(REMAIN_QTY,0)) rem_qty,
  SUM(COALESCE(TARGET_QTY,0)) tgt_qty
FROM TASKRSRC
WHERE PROJ_ID=?
  AND TARGET_END_DATE IS NOT NULL
  AND date(TARGET_END_DATE) BETWEEN date(?) AND date(?)
''',(PROJ,WS,WE)).fetchone()
print('END_IN_W09',dict(r2))

# task level for same week
r3=cur.execute('''
SELECT
  SUM(COALESCE(REMAIN_WORK_QTY,0)) rem_qty,
  SUM(COALESCE(TARGET_WORK_QTY,0)) tgt_qty,
  SUM(COALESCE(REMAIN_WORK_QTY,0)*COALESCE( (SELECT AVG(COST_PER_QTY) FROM TASKRSRC tr WHERE tr.TASK_ID=t.TASK_ID AND tr.PROJ_ID=t.PROJ_ID),0)) rem_cost_proxy
FROM TASK t
WHERE t.PROJ_ID=?
  AND t.TARGET_END_DATE IS NOT NULL
  AND date(t.TARGET_END_DATE) BETWEEN date(?) AND date(?)
''',(PROJ,WS,WE)).fetchone()
print('TASK_END_IN_W09',dict(r3))

# top assignments by remaining cost
rows=cur.execute('''
SELECT TASKRSRC_ID, TASK_ID, TARGET_END_DATE, REMAIN_COST, REMAIN_QTY, COST_PER_QTY
FROM TASKRSRC
WHERE PROJ_ID=?
ORDER BY REMAIN_COST DESC
LIMIT 20
''',(PROJ,)).fetchall()
print('TOP_REMAIN')
for x in rows:
  print(dict(x))

con.close()
