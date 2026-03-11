import sqlite3
from datetime import datetime, timedelta
from collections import defaultdict

DB = r"C:\Users\josej\OneDrive\Documentos\PPMDBSQLite_20221109_BBDD_JJC_Rev B.db"
PROJ_ID = 26257
CUTOFF = datetime(2026, 2, 22, 23, 59, 59)

con = sqlite3.connect(DB)
con.row_factory = sqlite3.Row
cur = con.cursor()

# Use TASKRSRC labor units as primary source to align with P6 usage concepts
rows = cur.execute(
    """
    SELECT TASK_ID,
           COALESCE(TARGET_QTY,0) AS BAC_HH,
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

if not rows:
    print("NO_TASKRSRC_DATA")
    raise SystemExit(0)


def dt(s):
    if not s:
        return None
    try:
        return datetime.strptime(s[:19], "%Y-%m-%d %H:%M:%S")
    except Exception:
        return None

# Snapshot totals at cutoff
bac = sum(float(r["BAC_HH"]) for r in rows)
actual = 0.0
remaining = 0.0

for r in rows:
    act_start = dt(r["ACT_START_DATE"])
    act_end = dt(r["ACT_END_DATE"])
    act_qty = float(r["ACT_HH"])
    rem_qty = float(r["REM_HH"])

    # If not started by cutoff, actual=0 and remaining as planned remaining
    if act_start is None or act_start > CUTOFF:
        actual += 0.0
        remaining += rem_qty if rem_qty > 0 else float(r["BAC_HH"])
        continue

    # Started by cutoff
    actual += act_qty

    # If finished by cutoff, remaining should be 0
    if act_end is not None and act_end <= CUTOFF:
        remaining += 0.0
    else:
        remaining += rem_qty

# Earned Value in labor units proxy: EV_HH = actualized progress units (ACT_HH)
ev_hh = actual
eac_hh = actual + remaining
etc_hh = remaining

# Percentages over BAC
pct_ev = (ev_hh / bac * 100.0) if bac else 0.0
pct_eac = (eac_hh / bac * 100.0) if bac else 0.0
pct_etc = (etc_hh / bac * 100.0) if bac else 0.0

print(f"PROJ_ID={PROJ_ID}|CUTOFF={CUTOFF}|ROWS={len(rows)}")
print(f"BAC_HH={bac:.3f}")
print("METRIC|HH|PCT_BAC")
print(f"EV|{ev_hh:.3f}|{pct_ev:.2f}")
print(f"EAC|{eac_hh:.3f}|{pct_eac:.2f}")
print(f"ETC|{etc_hh:.3f}|{pct_etc:.2f}")

# Weekly partial/cumulative EV up to cutoff (based on ACT dates spread labor-weekdays if both dates exist)
by_week = defaultdict(float)
for r in rows:
    act_hh = float(r["ACT_HH"])
    if act_hh <= 0:
        continue
    s = dt(r["ACT_START_DATE"])
    e = dt(r["ACT_END_DATE"])
    if s is None:
        continue
    if e is None or e > CUTOFF:
        e = CUTOFF
    if e < s:
        e = s

    # distribute across weekdays only
    days = []
    d = s.date()
    while d <= e.date():
        if d.weekday() < 5:
            days.append(d)
        d += timedelta(days=1)
    if not days:
        days = [s.date()]
    per = act_hh / len(days)
    for day in days:
        monday = day - timedelta(days=day.weekday())
        by_week[monday] += per

print("WEEK|EV_HH_WEEK|EV_HH_CUM|EV_%_CUM")
cum = 0.0
for monday in sorted(by_week):
    w = by_week[monday]
    cum += w
    y, iso_w, _ = monday.isocalendar()
    pct = (cum / bac * 100.0) if bac else 0.0
    print(f"ISO{y}-W{iso_w:02d}|{w:.3f}|{cum:.3f}|{pct:.2f}")

con.close()
