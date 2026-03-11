import sqlite3
from pathlib import Path

DB=Path(r"C:\Users\josej\OneDrive\Documentos\PPMDBSQLite_20221109_BBDD_JJC_Rev B - copia_WORK_20260226_145427.db")
PROJ_ID=26196
con=sqlite3.connect(DB)
con.row_factory=sqlite3.Row
cur=con.cursor()
rows=cur.execute('SELECT WBS_ID,PARENT_WBS_ID,WBS_SHORT_NAME,WBS_NAME,SEQ_NUM FROM PROJWBS WHERE PROJ_ID=? ORDER BY SEQ_NUM,WBS_ID',(PROJ_ID,)).fetchall()
print('count',len(rows))
for r in rows[:15]:
    print(r['WBS_ID'], r['PARENT_WBS_ID'], r['WBS_SHORT_NAME'], r['WBS_NAME'])
ids=set(r['WBS_ID'] for r in rows)
roots=[r for r in rows if r['PARENT_WBS_ID'] is None or r['PARENT_WBS_ID'] not in ids or r['PARENT_WBS_ID']==r['WBS_ID']]
print('roots',len(roots))
for r in roots[:10]:
    print('root',r['WBS_ID'],r['PARENT_WBS_ID'],r['WBS_SHORT_NAME'])
