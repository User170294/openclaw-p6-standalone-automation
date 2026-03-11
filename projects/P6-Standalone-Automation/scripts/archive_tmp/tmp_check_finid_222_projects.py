import sqlite3
DB = r"C:\Users\josej\OneDrive\Documentos\PPMDBSQLite_20221109_BBDD_JJC_Rev B.db"
con=sqlite3.connect(DB)
con.row_factory=sqlite3.Row
cur=con.cursor()
rows=cur.execute('''
SELECT PROJ_ID, COUNT(*) c, SUM(COALESCE(ACT_QTY,0)) act
FROM TRSRCFIN
WHERE FIN_DATES_ID=222
GROUP BY PROJ_ID
ORDER BY c DESC
''').fetchall()
print('ROWS',len(rows))
for r in rows:
    print(f"PROJ_ID={r['PROJ_ID']}|ROWS={r['c']}|ACT_QTY={r['act']}")
con.close()
