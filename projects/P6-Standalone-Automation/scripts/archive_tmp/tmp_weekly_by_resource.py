import argparse
import sqlite3
from datetime import datetime, timedelta

ap = argparse.ArgumentParser()
ap.add_argument('--db', required=True)
ap.add_argument('--proj-id', type=int, required=True)
ap.add_argument('--start', required=True)
ap.add_argument('--weeks', type=int, default=6)
args = ap.parse_args()

start = datetime.strptime(args.start, '%Y-%m-%d').date()

con = sqlite3.connect(args.db)
con.row_factory = sqlite3.Row
cur = con.cursor()

print(f"PROJ={args.proj_id}")
print("RESOURCES")
for r in cur.execute('''
SELECT tr.RSRC_ID, COALESCE(r.RSRC_SHORT_NAME,''), COALESCE(r.RSRC_NAME,''), COUNT(*) n, SUM(COALESCE(tr.TARGET_QTY,0)) hh
FROM TASKRSRC tr LEFT JOIN RSRC r ON r.RSRC_ID=tr.RSRC_ID
WHERE tr.PROJ_ID=?
GROUP BY tr.RSRC_ID, r.RSRC_SHORT_NAME, r.RSRC_NAME
ORDER BY tr.RSRC_ID
''',(args.proj_id,)).fetchall():
    print(f"RSRC|{r[0]}|{r[1]}|{r[2]}|ASG={r[3]}|HH={r[4]}")

print('WEEKLY_HH_BY_TARGET_END_AND_RESOURCE')
for i in range(args.weeks):
    ws = start + timedelta(days=7*i)
    we = ws + timedelta(days=6)
    print(f"WEEK|{ws}|{we}")
    rows = cur.execute('''
    SELECT tr.RSRC_ID, COALESCE(r.RSRC_SHORT_NAME,''), SUM(COALESCE(tr.TARGET_QTY,0)) hh
    FROM TASKRSRC tr
    LEFT JOIN RSRC r ON r.RSRC_ID=tr.RSRC_ID
    WHERE tr.PROJ_ID=?
      AND tr.TARGET_END_DATE IS NOT NULL
      AND date(tr.TARGET_END_DATE) BETWEEN date(?) AND date(?)
    GROUP BY tr.RSRC_ID, r.RSRC_SHORT_NAME
    ORDER BY tr.RSRC_ID
    ''',(args.proj_id, ws.isoformat(), we.isoformat())).fetchall()
    if not rows:
        print('  (sin HH en ese corte)')
    for rr in rows:
        print(f"  RSRC|{rr[0]}|{rr[1]}|HH={rr[2]}")

con.close()
