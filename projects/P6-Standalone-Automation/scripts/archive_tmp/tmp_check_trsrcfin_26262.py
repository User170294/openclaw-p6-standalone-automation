import sqlite3
DB = r"C:\Users\josej\OneDrive\Documentos\PPMDBSQLite_20221109_BBDD_JJC_Rev B.db"
con=sqlite3.connect(DB)
con.row_factory=sqlite3.Row
cur=con.cursor()
rows=cur.execute('''
SELECT tf.FIN_DATES_ID, fd.START_DATE, fd.END_DATE, SUM(tf.ACT_QTY) act
FROM TRSRCFIN tf
JOIN FINDATES fd ON fd.FIN_DATES_ID=tf.FIN_DATES_ID
WHERE tf.PROJ_ID=26262
GROUP BY tf.FIN_DATES_ID, fd.START_DATE, fd.END_DATE
ORDER BY fd.START_DATE
''').fetchall()
print('PERIODS',len(rows))
for r in rows:
    print(f"{r['FIN_DATES_ID']}|{r['START_DATE']}|{r['END_DATE']}|{r['act']}")
con.close()
