import argparse
import sqlite3
from pathlib import Path

ap = argparse.ArgumentParser()
ap.add_argument('--db', required=True)
args = ap.parse_args()

con = sqlite3.connect(Path(args.db))
con.row_factory = sqlite3.Row
cur = con.cursor()

cur.execute("""
SELECT PROJ_ID, PROJ_SHORT_NAME, PLAN_START_DATE, PLAN_END_DATE, LAST_SCHEDULE_DATE
FROM PROJECT
WHERE UPPER(COALESCE(PROJ_SHORT_NAME,'')) LIKE '%1844%'
ORDER BY PROJ_SHORT_NAME
""")
projects = cur.fetchall()

print(f"PROJECTS={len(projects)}")
for p in projects:
    proj_id = p['PROJ_ID']
    cur.execute('SELECT COUNT(*) c FROM TASK WHERE PROJ_ID=?', (proj_id,))
    total = cur.fetchone()['c']

    cur.execute("SELECT COUNT(*) c FROM TASK WHERE PROJ_ID=? AND (STATUS_CODE IS NULL OR STATUS_CODE<>'TK_Complete')", (proj_id,))
    open_tasks = cur.fetchone()['c']

    cur.execute("""
      SELECT COUNT(*) c
      FROM TASK t
      LEFT JOIN TASKPRED tp ON tp.TASK_ID=t.TASK_ID
      WHERE t.PROJ_ID=?
        AND tp.TASK_ID IS NULL
        AND (t.STATUS_CODE IS NULL OR t.STATUS_CODE<>'TK_Complete')
    """, (proj_id,))
    no_pred = cur.fetchone()['c']

    cur.execute("""
      SELECT COUNT(*) c
      FROM TASK t
      WHERE t.PROJ_ID=?
        AND t.TASK_TYPE IN ('TT_Mile','TT_FinMile','TT_LOE')
        AND t.TARGET_END_DATE IS NOT NULL
        AND datetime(t.TARGET_END_DATE) < datetime('now','localtime')
        AND (t.STATUS_CODE IS NULL OR t.STATUS_CODE<>'TK_Complete')
    """, (proj_id,))
    overdue = cur.fetchone()['c']

    print(f"{p['PROJ_ID']}|{p['PROJ_SHORT_NAME']}|start={p['PLAN_START_DATE']}|end={p['PLAN_END_DATE']}|last_sch={p['LAST_SCHEDULE_DATE']}|tasks={total}|open={open_tasks}|no_pred={no_pred}|overdue_miles={overdue}")
