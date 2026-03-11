import sqlite3
from datetime import datetime, timedelta
from collections import defaultdict

DB = r"C:\Users\josej\OneDrive\Documentos\PPMDBSQLite_20221109_BBDD_JJC_Rev B.db"
BASE_PROJ = 26258  # PV baseline
CURR_PROJ = 26262  # EV/ETC/EAC current
CUTOFF = datetime(2026, 2, 22, 23, 59, 59)

con = sqlite3.connect(DB)
con.row_factory = sqlite3.Row
cur = con.cursor()


def dt(s):
    if not s:
        return None
    try:
        return datetime.strptime(s[:19], "%Y-%m-%d %H:%M:%S")
    except Exception:
        return None

# ---- PV from baseline TASK target spread on weekdays ----
rows_pv = cur.execute(
    '''
    SELECT TARGET_START_DATE, TARGET_END_DATE, COALESCE(TARGET_WORK_QTY,0) AS HH
    FROM TASK
    WHERE PROJ_ID=?
      AND TARGET_START_DATE IS NOT NULL
      AND TARGET_END_DATE IS NOT NULL
      AND COALESCE(TARGET_WORK_QTY,0) > 0
    ''',
    (BASE_PROJ,),
).fetchall()

pv_week = defaultdict(float)
bac = 0.0
for r in rows_pv:
    s = dt(r['TARGET_START_DATE'])
    e = dt(r['TARGET_END_DATE'])
    if not s or not e:
        continue
    s = s.date(); e = e.date()
    if e < s:
        s, e = e, s
    hh = float(r['HH'])
    bac += hh

    days = []
    d = s
    while d <= e:
        if d.weekday() < 5:
            days.append(d)
        d += timedelta(days=1)
    if not days:
        days = [s]

    per = hh / len(days)
    for day in days:
        monday = day - timedelta(days=day.weekday())
        pv_week[monday] += per

# ---- EV weekly and ETC/EAC from current TASKRSRC snapshot at cutoff ----
rows = cur.execute(
    '''
    SELECT COALESCE(TARGET_QTY,0) AS BAC_HH,
           COALESCE(ACT_REG_QTY,0) AS ACT_HH,
           COALESCE(REMAIN_QTY,0) AS REM_HH,
           TARGET_START_DATE,
           TARGET_END_DATE,
           ACT_START_DATE,
           ACT_END_DATE
    FROM TASKRSRC
    WHERE PROJ_ID=?
    ''',
    (CURR_PROJ,),
).fetchall()

if not rows:
    print('NO_DATA_CURRENT')
    raise SystemExit(0)

ev_week = defaultdict(float)
etc_week = defaultdict(float)

ev_cutoff = 0.0
etc_total = 0.0

for r in rows:
    bac_i = float(r['BAC_HH'])
    act_i = float(r['ACT_HH'])
    rem_i = float(r['REM_HH'])

    t_start = dt(r['TARGET_START_DATE'])
    t_end = dt(r['TARGET_END_DATE'])
    a_start = dt(r['ACT_START_DATE'])
    a_end = dt(r['ACT_END_DATE'])

    # EV at cutoff and weekly EV spread
    if a_start is not None and a_start <= CUTOFF and act_i > 0:
        ev_cutoff += act_i

        s = a_start.date()
        e = (a_end if (a_end is not None and a_end <= CUTOFF) else CUTOFF).date()
        if e < s:
            e = s

        days = []
        d = s
        while d <= e:
            if d.weekday() < 5:
                days.append(d)
            d += timedelta(days=1)
        if not days:
            days = [s]

        per = act_i / len(days)
        for day in days:
            monday = day - timedelta(days=day.weekday())
            ev_week[monday] += per

    # ETC at cutoff
    if a_start is None or a_start > CUTOFF:
        rem_cut = rem_i if rem_i > 0 else bac_i
    elif a_end is not None and a_end <= CUTOFF:
        rem_cut = 0.0
    else:
        rem_cut = rem_i

    if rem_cut > 0:
        etc_total += rem_cut

        start = (CUTOFF + timedelta(seconds=1)).date()
        if t_start is not None and t_start.date() > start:
            start = t_start.date()
        end = t_end.date() if t_end is not None else start
        if end < start:
            end = start

        days = []
        d = start
        while d <= end:
            if d.weekday() < 5:
                days.append(d)
            d += timedelta(days=1)
        if not days:
            days = [start]

        per = rem_cut / len(days)
        for day in days:
            monday = day - timedelta(days=day.weekday())
            etc_week[monday] += per

# Build combined week axis
all_weeks = sorted(set(list(pv_week.keys()) + list(ev_week.keys()) + list(etc_week.keys())))

print(f"BASE_PROJ={BASE_PROJ}|CURR_PROJ={CURR_PROJ}|CUTOFF={CUTOFF}")
print(f"BAC_HH={bac:.3f}|EV_CUTOFF_HH={ev_cutoff:.3f}|ETC_TOTAL_HH={etc_total:.3f}|EAC_HH={(ev_cutoff+etc_total):.3f}")
print("WEEK|PV_HH_WEEK|PV_%_CUM|EV_HH_WEEK|EV_%_CUM|ETC_HH_WEEK|ETC_%_CUM|EAC_HH_CUM|EAC_%_CUM")

pv_c = ev_c = etc_c = 0.0
for m in all_weeks:
    pvw = pv_week.get(m, 0.0)
    evw = ev_week.get(m, 0.0)
    etcw = etc_week.get(m, 0.0)

    pv_c += pvw
    ev_c += evw
    etc_c += etcw

    eac_c = ev_cutoff + etc_c

    pv_pct = (pv_c / bac * 100.0) if bac else 0.0
    ev_pct = (ev_c / bac * 100.0) if bac else 0.0
    etc_pct = (etc_c / bac * 100.0) if bac else 0.0
    eac_pct = (eac_c / bac * 100.0) if bac else 0.0

    y, w, _ = m.isocalendar()
    print(f"ISO{y}-W{w:02d}|{pvw:.3f}|{pv_pct:.2f}|{evw:.3f}|{ev_pct:.2f}|{etcw:.3f}|{etc_pct:.2f}|{eac_c:.3f}|{eac_pct:.2f}")

con.close()
