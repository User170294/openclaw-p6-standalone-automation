import sqlite3
DB=r"C:\Users\josej\OneDrive\Documentos\PPMDBSQLite_20221109_BBDD_JJC_Rev B.db"
con=sqlite3.connect(DB)
con.row_factory=sqlite3.Row
cur=con.cursor()
projects=[26258,26197,26198,26262,26261]
for p in projects:
    r=cur.execute('SELECT PROJ_SHORT_NAME FROM PROJECT WHERE PROJ_ID=?',(p,)).fetchone()
    name=r['PROJ_SHORT_NAME'] if r else ''
    week=cur.execute('''
      SELECT SUM(COALESCE(REMAIN_COST,0)) rem_w, SUM(COALESCE(TARGET_COST,0)) pv_w
      FROM TASKRSRC
      WHERE PROJ_ID=? AND TARGET_END_DATE IS NOT NULL
        AND date(TARGET_END_DATE) BETWEEN date('2026-02-23') AND date('2026-03-01')
    ''',(p,)).fetchone()
    snap=cur.execute('SELECT SUM(COALESCE(ACT_REG_COST,0)+COALESCE(ACT_OT_COST,0)) ac, SUM(COALESCE(REMAIN_COST,0)) rem FROM TASKRSRC WHERE PROJ_ID=?',(p,)).fetchone()
    print(p,name,'week_rem',week['rem_w'],'week_pv',week['pv_w'],'ac',snap['ac'],'rem',snap['rem'],'cum_eac_w09', (snap['ac'] or 0)+(week['rem_w'] or 0))
con.close()
