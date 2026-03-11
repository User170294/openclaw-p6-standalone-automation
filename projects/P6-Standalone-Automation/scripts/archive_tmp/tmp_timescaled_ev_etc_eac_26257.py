import sqlite3
from datetime import datetime
from collections import defaultdict

DB = r"C:\Users\josej\OneDrive\Documentos\PPMDBSQLite_20221109_BBDD_JJC_Rev B.db"
PROJ_ID = 26257

con = sqlite3.connect(DB)
con.row_factory = sqlite3.Row
cur = con.cursor()

# BAC from TASKRSRC snapshot
bac = cur.execute(
    "SELECT COALESCE(SUM(TARGET_QTY),0) AS v FROM TASKRSRC WHERE PROJ_ID=?",
    (PROJ_ID,),
).fetchone()["v"]

# Period actuals from TRSRCFIN + FINDATES
rows = cur.execute(
    """
    SELECT fd.START_DATE, fd.END_DATE, COALESCE(SUM(tf.ACT_QTY),0) AS ACT_HH
    FROM TRSRCFIN tf
    JOIN FINDATES fd ON fd.FIN_DATES_ID = tf.FIN_DATES_ID
    WHERE tf.PROJ_ID=?
    GROUP BY tf.FIN_DATES_ID, fd.START_DATE, fd.END_DATE
    ORDER BY fd.START_DATE
    """,
    (PROJ_ID,),
).fetchall()

print(f"PROJ_ID={PROJ_ID}|BAC_HH={bac:.3f}|PERIODS={len(rows)}")
print("WEEK|START|END|EV_HH_WEEK|EV_HH_CUM|EV_%_CUM|ETC_HH|ETC_%|EAC_HH|EAC_%")

ev_cum = 0.0
for r in rows:
    start = datetime.strptime(r["START_DATE"][:19], "%Y-%m-%d %H:%M:%S").date()
    end = datetime.strptime(r["END_DATE"][:19], "%Y-%m-%d %H:%M:%S").date()
    ev_w = float(r["ACT_HH"])
    ev_cum += ev_w

    etc = max(0.0, float(bac) - ev_cum)
    eac = ev_cum + etc  # stays BAC when ETC is BAC-EV

    y, w, _ = start.isocalendar()
    ev_pct = (ev_cum / bac * 100.0) if bac else 0.0
    etc_pct = (etc / bac * 100.0) if bac else 0.0
    eac_pct = (eac / bac * 100.0) if bac else 0.0

    print(f"ISO{y}-W{w:02d}|{start}|{end}|{ev_w:.3f}|{ev_cum:.3f}|{ev_pct:.2f}|{etc:.3f}|{etc_pct:.2f}|{eac:.3f}|{eac_pct:.2f}")

con.close()
