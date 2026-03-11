import sqlite3
from datetime import datetime, timedelta
from collections import defaultdict

DB = r"C:\Users\josej\OneDrive\Documentos\PPMDBSQLite_20221109_BBDD_JJC_Rev B.db"
PROJ_ID = 26257
CUTOFF = datetime(2026, 2, 22, 23, 59, 59)

con = sqlite3.connect(DB)
con.row_factory = sqlite3.Row
cur = con.cursor()

rows = cur.execute(
    """
    SELECT COALESCE(TARGET_QTY,0) AS BAC_HH,
           COALESCE(ACT_REG_QTY,0) AS ACT_HH,
           COALESCE(REMAIN_QTY,0) AS REM_HH,
           TARGET_START_DATE,
           TARGET_END_DATE,
           ACT_START_DATE,
           ACT_END_DATE
    FROM TASKRSRC
    WHERE PROJ_ID=?
    """,
    (PROJ_ID,),
).fetchall()


def dt(s):
    if not s:
        return None
    try:
        return datetime.strptime(s[:19], "%Y-%m-%d %H:%M:%S")
    except Exception:
        return None

if not rows:
    print("NO_DATA")
    raise SystemExit(0)

bac = sum(float(r["BAC_HH"]) for r in rows)
ev_cutoff = 0.0
etc_total = 0.0

etc_week = defaultdict(float)

for r in rows:
    bac_i = float(r["BAC_HH"])
    act_i = float(r["ACT_HH"])
    rem_i = float(r["REM_HH"])

    t_start = dt(r["TARGET_START_DATE"])
    t_end = dt(r["TARGET_END_DATE"])
    a_start = dt(r["ACT_START_DATE"])
    a_end = dt(r["ACT_END_DATE"])

    # EV al corte
    if a_start is not None and a_start <= CUTOFF:
        ev_cutoff += act_i

    # ETC al corte por asignación
    if a_start is None or a_start > CUTOFF:
        rem_cut = rem_i if rem_i > 0 else bac_i
    elif a_end is not None and a_end <= CUTOFF:
        rem_cut = 0.0
    else:
        rem_cut = rem_i

    if rem_cut <= 0:
        continue

    etc_total += rem_cut

    # Ventana de distribución futura (L-V)
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

print(f"PROJ_ID={PROJ_ID}|CUTOFF={CUTOFF}|BAC_HH={bac:.3f}|EV_CUTOFF_HH={ev_cutoff:.3f}|ETC_TOTAL_HH={etc_total:.3f}")
print("WEEK|ETC_HH_WEEK|ETC_HH_CUM|ETC_%_CUM|EAC_HH_WEEK|EAC_HH_CUM|EAC_%_CUM")

etc_cum = 0.0
for monday in sorted(etc_week):
    eweek = etc_week[monday]
    etc_cum += eweek
    eac_week = eweek
    eac_cum = ev_cutoff + etc_cum

    etc_pct = (etc_cum / bac * 100.0) if bac else 0.0
    eac_pct = (eac_cum / bac * 100.0) if bac else 0.0

    y, w, _ = monday.isocalendar()
    print(f"ISO{y}-W{w:02d}|{eweek:.3f}|{etc_cum:.3f}|{etc_pct:.2f}|{eac_week:.3f}|{eac_cum:.3f}|{eac_pct:.2f}")

con.close()
