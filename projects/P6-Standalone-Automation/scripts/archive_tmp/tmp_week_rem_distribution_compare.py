import sqlite3
from datetime import datetime, timedelta
DB=r"C:\Users\josej\OneDrive\Documentos\PPMDBSQLite_20221109_BBDD_JJC_Rev B.db"
con=sqlite3.connect(DB); con.row_factory=sqlite3.Row; cur=con.cursor()
rows=cur.execute('SELECT TARGET_START_DATE,TARGET_END_DATE,ACT_START_DATE,ACT_END_DATE,COALESCE(TARGET_QTY,0) bac,COALESCE(REMAIN_QTY,0) rem FROM TASKRSRC WHERE PROJ_ID=26262').fetchall()
cut=datetime(2026,2,22,23,59,59)
ws=datetime(2026,2,23).date(); we=datetime(2026,3,1).date()

def dt(s):
    if not s:return None
    return datetime.strptime(s[:19],'%Y-%m-%d %H:%M:%S')

for mode in ['weekdays','alldays']:
    w=0.0
    for r in rows:
        bac=float(r['bac']); rem=float(r['rem'])
        astart=dt(r['ACT_START_DATE']); aend=dt(r['ACT_END_DATE'])
        tstart=dt(r['TARGET_START_DATE']); tend=dt(r['TARGET_END_DATE'])
        if astart is None or astart>cut: rem_cut= rem if rem>0 else bac
        elif aend is not None and aend<=cut: rem_cut=0.0
        else: rem_cut=rem
        if rem_cut<=0: continue
        s=(cut+timedelta(seconds=1)).date()
        if tstart and tstart.date()>s: s=tstart.date()
        e=tend.date() if tend else s
        if e<s: e=s
        days=[]; d=s
        while d<=e:
            if mode=='alldays' or d.weekday()<5: days.append(d)
            d+=timedelta(days=1)
        if not days: days=[s]
        per=rem_cut/len(days)
        for d in days:
            if ws<=d<=we: w+=per
    print(mode,w)
con.close()
