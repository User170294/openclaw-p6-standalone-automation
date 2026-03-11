import argparse
import sqlite3
from datetime import datetime

ap = argparse.ArgumentParser()
ap.add_argument('--db', required=True)
ap.add_argument('--proj-id', type=int, required=True)
ap.add_argument('--start', required=True, help='YYYY-MM-DD')
ap.add_argument('--end', required=True, help='YYYY-MM-DD')
args = ap.parse_args()

con = sqlite3.connect(args.db)
con.row_factory = sqlite3.Row
cur = con.cursor()

proj = cur.execute("SELECT PROJ_SHORT_NAME, PLAN_START_DATE, PLAN_END_DATE, LAST_SCHEDULE_DATE FROM PROJECT WHERE PROJ_ID=?", (args.proj_id,)).fetchone()
print(f"PROJ_ID={args.proj_id}|NAME={proj['PROJ_SHORT_NAME'] if proj else ''}|PLAN_START={proj['PLAN_START_DATE'] if proj else ''}|PLAN_END={proj['PLAN_END_DATE'] if proj else ''}|LAST_SCH={proj['LAST_SCHEDULE_DATE'] if proj else ''}")

sumr = cur.execute(
    """
    SELECT COUNT(*) AS total,
           SUM(CASE WHEN STATUS_CODE='TK_Complete' THEN 1 ELSE 0 END) AS done,
           AVG(COALESCE(PHYS_COMPLETE_PCT,0)) AS avg_phys,
           SUM(COALESCE(TARGET_WORK_QTY,0)) AS target_work,
           SUM(COALESCE(ACT_WORK_QTY,0)) AS act_work,
           SUM(COALESCE(REMAIN_WORK_QTY,0)) AS rem_work
    FROM TASK
    WHERE PROJ_ID=?
    """,
    (args.proj_id,),
).fetchone()

print(f"SUMMARY|TOTAL={sumr['total'] or 0}|DONE={sumr['done'] or 0}|AVG_PHYS={round(sumr['avg_phys'] or 0,2)}|TARGET_WORK={sumr['target_work'] or 0}|ACT_WORK={sumr['act_work'] or 0}|REMAIN_WORK={sumr['rem_work'] or 0}")

# Activities planned in the week window by target dates
rows = cur.execute(
    """
    SELECT TASK_ID, COALESCE(TASK_CODE,'') AS TASK_CODE, COALESCE(TASK_NAME,'') AS TASK_NAME,
           COALESCE(STATUS_CODE,'') AS STATUS_CODE,
           TARGET_START_DATE, TARGET_END_DATE,
           COALESCE(PHYS_COMPLETE_PCT,0) AS PHYS,
           COALESCE(TARGET_WORK_QTY,0) AS TGT_WORK,
           COALESCE(ACT_WORK_QTY,0) AS ACT_WORK,
           COALESCE(REMAIN_WORK_QTY,0) AS REM_WORK
    FROM TASK
    WHERE PROJ_ID=?
      AND (
        date(COALESCE(TARGET_START_DATE, TARGET_END_DATE)) BETWEEN date(?) AND date(?)
        OR date(COALESCE(TARGET_END_DATE, TARGET_START_DATE)) BETWEEN date(?) AND date(?)
      )
    ORDER BY datetime(COALESCE(TARGET_START_DATE, TARGET_END_DATE)), TASK_CODE
    """,
    (args.proj_id, args.start, args.end, args.start, args.end),
).fetchall()

print(f"WEEK_WINDOW={args.start}..{args.end}|PLANNED_ROWS={len(rows)}")
for r in rows:
    print(f"PLAN|{r['TASK_CODE']}|{r['TASK_NAME']}|STATUS={r['STATUS_CODE']}|TS={r['TARGET_START_DATE']}|TE={r['TARGET_END_DATE']}|PHYS={r['PHYS']}|TGTW={r['TGT_WORK']}|ACTW={r['ACT_WORK']}|REMW={r['REM_WORK']}")

pending = [r for r in rows if r['STATUS_CODE'] != 'TK_Complete']
print(f"WEEK_PENDING={len(pending)}")
for r in pending:
    print(f"PEND|{r['TASK_CODE']}|{r['TASK_NAME']}|TS={r['TARGET_START_DATE']}|TE={r['TARGET_END_DATE']}|PHYS={r['PHYS']}|REMW={r['REM_WORK']}")

con.close()
