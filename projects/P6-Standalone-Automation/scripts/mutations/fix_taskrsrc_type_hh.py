import sqlite3
DB = r"C:\Users\josej\OneDrive\Documentos\PPMDBSQLite_20221109_BBDD_JJC_Rev B - copia_WORK_20260226_145427.db"
con=sqlite3.connect(DB)
cur=con.cursor()
cur.execute('''
update TASKRSRC
set RSRC_TYPE='RT_Labor'
where PROJ_ID=26196 and RSRC_ID between 9555 and 9569
''')
print(f'UPDATED={cur.rowcount}')
con.commit()
con.close()
