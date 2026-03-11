import sqlite3
from datetime import datetime, timedelta, date
from collections import defaultdict

DB = r"C:\Users\josej\OneDrive\Documentos\PPMDBSQLite_20221109_BBDD_JJC_Rev B.db"
PROJ_ID = 26258

con = sqlite3.connect(DB)
con.row_factory = sqlite3.Row
cur = con.cursor()
rows = cur.execute("SELECT TARGET_START_DATE, TARGET_END_DATE, COALESCE(TARGET_WORK_QTY,0) HH FROM TASK WHERE PROJ_ID=? AND TARGET_START_DATE IS NOT NULL AND TARGET_END_DATE IS NOT NULL AND COALESCE(TARGET_WORK_QTY,0)>0", (PROJ_ID,)).fetchall()

def d(s): return datetime.strptime(s[:19], '%Y-%m-%d %H:%M:%S').date()

by_day = defaultdict(float)
for r in rows:
    s,e=d(r['TARGET_START_DATE']),d(r['TARGET_END_DATE'])
    if e<s: s,e=e,s
    days=[]
    x=s
    while x<=e:
        if x.weekday()<5:
            days.append(x)
        x += timedelta(days=1)
    if not days:
        days=[s]
    per=float(r['HH'])/len(days)
    for x in days: by_day[x]+=per

weeks=defaultdict(float)
for k,v in by_day.items():
    m=k-timedelta(days=k.weekday())
    weeks[m]+=v

tot=sum(r['HH'] for r in rows)
c=0
for m in sorted(weeks):
    c+=weeks[m]
    y,w,_=m.isocalendar()
    print(f"ISO{y}-W{w:02d}|{m}|{round(weeks[m],3)}|{round(c,3)}|{round(c/tot*100,2)}")

con.close()
