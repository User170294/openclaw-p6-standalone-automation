import argparse
import sqlite3
from pathlib import Path

ap = argparse.ArgumentParser()
ap.add_argument('--db', required=True)
ap.add_argument('--proj-id', type=int, required=True)
args = ap.parse_args()

con = sqlite3.connect(Path(args.db))
con.row_factory = sqlite3.Row
cur = con.cursor()

cur.execute('SELECT PROJ_ID, PROJ_SHORT_NAME, PLAN_START_DATE, PLAN_END_DATE, LAST_SCHEDULE_DATE FROM PROJECT WHERE PROJ_ID=?', (args.proj_id,))
r = cur.fetchone()
print('PROJECT')
print(dict(r) if r else 'NOT_FOUND')

cur.execute('SELECT COUNT(*) AS c FROM TASK WHERE PROJ_ID=?', (args.proj_id,))
print('TASK_TOTAL', cur.fetchone()['c'])

print('STATUS_COUNTS')
cur.execute('SELECT COALESCE(STATUS_CODE, "(null)") AS status, COUNT(*) AS c FROM TASK WHERE PROJ_ID=? GROUP BY COALESCE(STATUS_CODE, "(null)") ORDER BY c DESC', (args.proj_id,))
for x in cur.fetchall():
    print(f"{x['status']}|{x['c']}")
