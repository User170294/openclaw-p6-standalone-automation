import sqlite3
DB = r"C:\Users\josej\OneDrive\Documentos\PPMDBSQLite_20221109_BBDD_JJC_Rev B.db"
con=sqlite3.connect(DB)
con.row_factory=sqlite3.Row
cur=con.cursor()
rows=cur.execute('''
SELECT tf.FIN_DATES_ID, tf.TASKRSRC_ID, tf.TASK_ID, tf.ACT_QTY, fd.FIN_DATES_NAME, fd.START_DATE, fd.END_DATE
FROM TRSRCFIN tf
LEFT JOIN FINDATES fd ON fd.FIN_DATES_ID=tf.FIN_DATES_ID
WHERE tf.PROJ_ID=?
ORDER BY tf.FIN_DATES_ID, tf.TASKRSRC_ID
''',(26257,)).fetchall()
print('ROWS',len(rows))
for r in rows[:40]:
    print(f"{r['FIN_DATES_ID']}|{r['TASKRSRC_ID']}|{r['TASK_ID']}|{r['ACT_QTY']}|{r['FIN_DATES_NAME']}|{r['START_DATE']}|{r['END_DATE']}")
con.close()
