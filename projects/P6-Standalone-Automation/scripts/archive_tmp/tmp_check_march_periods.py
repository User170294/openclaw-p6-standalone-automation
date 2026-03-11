import sqlite3
DB = r"C:\Users\josej\OneDrive\Documentos\PPMDBSQLite_20221109_BBDD_JJC_Rev B.db"
con=sqlite3.connect(DB)
con.row_factory=sqlite3.Row
cur=con.cursor()
rows=cur.execute('''
SELECT FIN_DATES_ID, FIN_DATES_NAME, START_DATE, END_DATE
FROM FINDATES
WHERE date(START_DATE) BETWEEN date('2026-03-01') AND date('2026-03-31')
   OR date(END_DATE) BETWEEN date('2026-03-01') AND date('2026-03-31')
ORDER BY START_DATE
''').fetchall()
for r in rows:
    print(f"{r['FIN_DATES_ID']}|{r['FIN_DATES_NAME']}|{r['START_DATE']}|{r['END_DATE']}")
con.close()
