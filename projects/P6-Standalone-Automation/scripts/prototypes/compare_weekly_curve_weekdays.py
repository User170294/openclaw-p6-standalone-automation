import argparse
import sqlite3
from datetime import datetime, timedelta, date
from collections import defaultdict

ap = argparse.ArgumentParser()
ap.add_argument('--db', required=True)
ap.add_argument('--base-proj', type=int, required=True)
ap.add_argument('--prog-proj', type=int, required=True)
ap.add_argument('--start', default='2026-02-02', help='Inicio semana W06 (YYYY-MM-DD)')
ap.add_argument('--weeks', type=int, default=10)
args = ap.parse_args()

start = datetime.strptime(args.start, '%Y-%m-%d').date()

con = sqlite3.connect(args.db)
con.row_factory = sqlite3.Row
cur = con.cursor()

def proj_name(pid):
    r = cur.execute('SELECT PROJ_SHORT_NAME FROM PROJECT WHERE PROJ_ID=?', (pid,)).fetchone()
    return r['PROJ_SHORT_NAME'] if r else str(pid)

def weekly_timephased(pid):
    rows = cur.execute(
        """
        SELECT TARGET_START_DATE, TARGET_END_DATE, COALESCE(TARGET_WORK_QTY,0) HH
        FROM TASK
        WHERE PROJ_ID=?
          AND TARGET_START_DATE IS NOT NULL
          AND TARGET_END_DATE IS NOT NULL
          AND COALESCE(TARGET_WORK_QTY,0) > 0
        """,
        (pid,),
    ).fetchall()

    by_day = defaultdict(float)
    total = 0.0

    for r in rows:
        s = datetime.strptime(r['TARGET_START_DATE'][:19], '%Y-%m-%d %H:%M:%S').date()
        e = datetime.strptime(r['TARGET_END_DATE'][:19], '%Y-%m-%d %H:%M:%S').date()
        if e < s:
            s, e = e, s
        hh = float(r['HH'] or 0.0)
        total += hh

        workdays = []
        d = s
        while d <= e:
            if d.weekday() < 5:
                workdays.append(d)
            d += timedelta(days=1)
        if not workdays:
            workdays = [s]

        per_day = hh / len(workdays) if workdays else 0.0
        for d in workdays:
            monday = d - timedelta(days=d.weekday())
            by_day[monday] += per_day

    return total, by_day

base_total, base_week = weekly_timephased(args.base_proj)
prog_total, prog_week = weekly_timephased(args.prog_proj)

print(f"BASE={args.base_proj}|{proj_name(args.base_proj)}|TOTAL_HH={round(base_total,3)}")
print(f"PROG={args.prog_proj}|{proj_name(args.prog_proj)}|TOTAL_HH={round(prog_total,3)}")
print('WEEK|START|BASE_HH_WEEK|BASE_%_CUM|PROG_HH_WEEK|PROG_%_CUM|DELTA_HH_WEEK(P-B)|DELTA_%_CUM(P-B)')

b_cum = 0.0
p_cum = 0.0
for i in range(args.weeks):
    ws = start + timedelta(days=7*i)
    b = float(base_week.get(ws, 0.0))
    p = float(prog_week.get(ws, 0.0))
    b_cum += b
    p_cum += p
    b_pct = (b_cum / base_total * 100.0) if base_total else 0.0
    p_pct = (p_cum / prog_total * 100.0) if prog_total else 0.0
    y, w, _ = ws.isocalendar()
    print(f"ISO{y}-W{w:02d}|{ws}|{round(b,3)}|{round(b_pct,2)}|{round(p,3)}|{round(p_pct,2)}|{round(p-b,3)}|{round(p_pct-b_pct,2)}")

con.close()
