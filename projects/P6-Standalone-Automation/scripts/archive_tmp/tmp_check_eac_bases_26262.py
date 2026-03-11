import sqlite3
DB=r"C:\Users\josej\OneDrive\Documentos\PPMDBSQLite_20221109_BBDD_JJC_Rev B.db"
con=sqlite3.connect(DB)
con.row_factory=sqlite3.Row
cur=con.cursor()
proj=26262
r1=cur.execute('SELECT SUM(COALESCE(TARGET_QTY,0)) bac, SUM(COALESCE(ACT_REG_QTY,0)) act, SUM(COALESCE(REMAIN_QTY,0)) rem FROM TASKRSRC WHERE PROJ_ID=?',(proj,)).fetchone()
r2=cur.execute('SELECT SUM(COALESCE(TARGET_WORK_QTY,0)) bac, SUM(COALESCE(ACT_WORK_QTY,0)) act, SUM(COALESCE(REMAIN_WORK_QTY,0)) rem FROM TASK WHERE PROJ_ID=?',(proj,)).fetchone()
print('TASKRSRC',dict(r1), 'EAC', (r1['act'] or 0)+(r1['rem'] or 0))
print('TASK',dict(r2), 'EAC', (r2['act'] or 0)+(r2['rem'] or 0))
con.close()
