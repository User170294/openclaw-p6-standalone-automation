import argparse
import sqlite3
from datetime import datetime, timedelta, date
from collections import defaultdict

ap = argparse.ArgumentParser()
ap.add_argument('--db', required=True)
ap.add_argument('--proj-id', type=int, required=True)
args = ap.parse_args()

con = sqlite3.connect(args.db)
con.row_factory = sqlite3.Row
cur = con.cursor()

rows = cur.execute(
    '''
    SELECT TASK_CODE, TARGET_START_DATE, TARGET_END_DATE, COALESCE(TARGET_WORK_QTY,0) AS HH
    FROM TASK
    WHERE PROJ_ID=?
      AND TARGET_START_DATE IS NOT NULL
      AND TARGET_END_DATE IS NOT NULL
      AND COALESCE(TARGET_WORK_QTY,0) > 0
    ''',
    (args.proj_id,),
).fetchall()

if not rows:
    print('NO_DATA')
    raise SystemExit(0)

def to_date(s):
    return datetime.strptime(s[:19], '%Y-%m-%d %H:%M:%S').date()

# Week convention from memory: W08 = 2026-02-16..2026-02-22 (Monday start)
w08_start = date(2026, 2, 16)

def week_label(d: date):
    if d < w08_start:
        # fallback ISO-like label for pre-W08 dates
        y, w, _ = d.isocalendar()
        return f'ISO{y}-W{w:02d}'
    delta_days = (d - w08_start).days
    wnum = 8 + (delta_days // 7)
    return f'W{wnum:02d}'

def week_bounds(d: date):
    monday = d - timedelta(days=d.weekday())
    sunday = monday + timedelta(days=6)
    return monday, sunday

weekly = defaultdict(float)
min_day = None
max_day = None

for r in rows:
    s = to_date(r['TARGET_START_DATE'])
    e = to_date(r['TARGET_END_DATE'])
    if e < s:
        s, e = e, s
    days = (e - s).days + 1
    if days <= 0:
        continue
    per_day = float(r['HH']) / days

    d = s
    while d <= e:
        weekly[d] += per_day
        d += timedelta(days=1)

    min_day = s if min_day is None or s < min_day else min_day
    max_day = e if max_day is None or e > max_day else max_day

# Aggregate by week monday
by_week = defaultdict(float)
for d, hh in weekly.items():
    monday = d - timedelta(days=d.weekday())
    by_week[monday] += hh

total = sum(float(r['HH']) for r in rows)

print(f'PROJ_ID={args.proj_id}|TOTAL_TARGET_HH={round(total,3)}|TASKS={len(rows)}')
print('WEEK|START|END|PLAN_HH_WEEK|PLAN_HH_CUM|PLAN_%_CUM')

cum = 0.0
for monday in sorted(by_week.keys()):
    hh = by_week[monday]
    cum += hh
    lbl = week_label(monday)
    end = monday + timedelta(days=6)
    pct = (cum / total * 100.0) if total else 0.0
    print(f'{lbl}|{monday}|{end}|{round(hh,3)}|{round(cum,3)}|{round(pct,2)}')

con.close()
