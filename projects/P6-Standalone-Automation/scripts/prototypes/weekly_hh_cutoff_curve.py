import argparse
import sqlite3
from datetime import date, datetime, timedelta

ap = argparse.ArgumentParser()
ap.add_argument('--db', required=True)
ap.add_argument('--proj-id', type=int, required=True)
ap.add_argument('--start-week', default='2026-02-16', help='Inicio W08 (YYYY-MM-DD)')
ap.add_argument('--weeks', type=int, default=10)
args = ap.parse_args()

w08_start = datetime.strptime(args.start_week, '%Y-%m-%d').date()

con = sqlite3.connect(args.db)
con.row_factory = sqlite3.Row
cur = con.cursor()

proj = cur.execute('SELECT PROJ_SHORT_NAME FROM PROJECT WHERE PROJ_ID=?', (args.proj_id,)).fetchone()
name = proj['PROJ_SHORT_NAME'] if proj else ''

total_hh = cur.execute(
    'SELECT COALESCE(SUM(TARGET_WORK_QTY),0) AS hh FROM TASK WHERE PROJ_ID=?',
    (args.proj_id,),
).fetchone()['hh']

print(f"PROJ_ID={args.proj_id}|NAME={name}|TOTAL_TARGET_HH={round(total_hh,3)}")
print('WEEK|START|END|PLAN_HH_WEEK(end_in_week)|PLAN_HH_CUM(end<=week)|PLAN_%_CUM')

for i in range(args.weeks):
    ws = w08_start + timedelta(days=7 * i)
    we = ws + timedelta(days=6)
    wnum = 8 + i
    label = f"W{wnum:02d}"

    week_hh = cur.execute(
        '''
        SELECT COALESCE(SUM(TARGET_WORK_QTY),0) AS hh
        FROM TASK
        WHERE PROJ_ID=?
          AND TARGET_END_DATE IS NOT NULL
          AND date(TARGET_END_DATE) BETWEEN date(?) AND date(?)
        ''',
        (args.proj_id, ws.isoformat(), we.isoformat()),
    ).fetchone()['hh']

    cum_hh = cur.execute(
        '''
        SELECT COALESCE(SUM(TARGET_WORK_QTY),0) AS hh
        FROM TASK
        WHERE PROJ_ID=?
          AND TARGET_END_DATE IS NOT NULL
          AND date(TARGET_END_DATE) <= date(?)
        ''',
        (args.proj_id, we.isoformat()),
    ).fetchone()['hh']

    pct = (cum_hh / total_hh * 100.0) if total_hh else 0.0
    print(f"{label}|{ws}|{we}|{round(week_hh,3)}|{round(cum_hh,3)}|{round(pct,2)}")

con.close()
