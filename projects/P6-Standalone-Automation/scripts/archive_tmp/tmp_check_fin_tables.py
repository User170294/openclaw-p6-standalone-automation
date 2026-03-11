import sqlite3
DB = r"C:\Users\josej\OneDrive\Documentos\PPMDBSQLite_20221109_BBDD_JJC_Rev B.db"
con=sqlite3.connect(DB)
con.row_factory=sqlite3.Row
cur=con.cursor()
print('TRSRCFIN_ROWS_26257=', cur.execute('SELECT COUNT(*) c FROM TRSRCFIN WHERE PROJ_ID=?',(26257,)).fetchone()['c'])
print('TABLES_FIN_DATE=')
for r in cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND UPPER(name) LIKE '%FIN%DATE%' ORDER BY name"):
    print('-', r['name'])
if cur.execute("SELECT COUNT(*) c FROM sqlite_master WHERE type='table' AND name='FINDATES'").fetchone()['c']:
    print('FINDATES_SAMPLE=')
    for r in cur.execute('SELECT * FROM FINDATES ORDER BY FIN_DATES_ID DESC LIMIT 5'):
        print(dict(r))
con.close()
