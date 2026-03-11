import argparse
import sqlite3
from datetime import datetime

ap=argparse.ArgumentParser()
ap.add_argument('--db',required=True)
ap.add_argument('--proj-id',type=int,required=True)
ap.add_argument('--start',required=True)
ap.add_argument('--end',required=True)
args=ap.parse_args()

con=sqlite3.connect(args.db)
con.row_factory=sqlite3.Row
cur=con.cursor()

total=cur.execute("SELECT SUM(COALESCE(TARGET_WORK_QTY,0)) FROM TASK WHERE PROJ_ID=?",(args.proj_id,)).fetchone()[0] or 0

# Conservative EV-plan: activities with target end <= cut date should be complete
cum=cur.execute(
"""
SELECT SUM(COALESCE(TARGET_WORK_QTY,0))
FROM TASK
WHERE PROJ_ID=? AND TARGET_END_DATE IS NOT NULL AND date(TARGET_END_DATE)<=date(?)
""",(args.proj_id,args.end)).fetchone()[0] or 0

# Week planned workload by overlap with week window
week=cur.execute(
"""
SELECT SUM(COALESCE(TARGET_WORK_QTY,0))
FROM TASK
WHERE PROJ_ID=?
  AND TARGET_START_DATE IS NOT NULL AND TARGET_END_DATE IS NOT NULL
  AND date(TARGET_END_DATE)>=date(?)
  AND date(TARGET_START_DATE)<=date(?)
""",(args.proj_id,args.start,args.end)).fetchone()[0] or 0

# Count activities finishing by cut
nfinish=cur.execute("SELECT COUNT(*) FROM TASK WHERE PROJ_ID=? AND TARGET_END_DATE IS NOT NULL AND date(TARGET_END_DATE)<=date(?)",(args.proj_id,args.end)).fetchone()[0]

print(f"PROJ={args.proj_id}|TOTAL_TARGET_WORK={total}")
print(f"WEEK={args.start}..{args.end}|PLANNED_WEEK_WORK={week}")
print(f"CUT={args.end}|PLANNED_CUM_WORK={cum}|PLANNED_CUM_PCT={round((cum/total*100) if total else 0,2)}|TASKS_FINISH_BY_CUT={nfinish}")

con.close()
