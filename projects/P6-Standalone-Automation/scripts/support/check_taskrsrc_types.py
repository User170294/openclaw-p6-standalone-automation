import sqlite3
DB = r"C:\Users\josej\OneDrive\Documentos\PPMDBSQLite_20221109_BBDD_JJC_Rev B - copia_WORK_20260226_145427.db"
con=sqlite3.connect(DB)
cur=con.cursor()
q='''
select RSRC_TYPE, count(*)
from TASKRSRC
where PROJ_ID=26196 and RSRC_ID between 9555 and 9569
group by RSRC_TYPE
'''
for r in cur.execute(q):
    print('|'.join(str(x) for x in r))
con.close()
