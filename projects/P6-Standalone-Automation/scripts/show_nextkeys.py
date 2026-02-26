import sqlite3
from pathlib import Path

DB = Path(r"C:\Users\josej\OneDrive\Documentos\PPMDBSQLite_20221109_BBDD_JJC_Rev B - copia_WORK_20260226_145427.db")
con = sqlite3.connect(DB)
con.row_factory = sqlite3.Row
cur = con.cursor()
rows = cur.execute("SELECT KEY_NAME, KEY_SEQ_NUM FROM NEXTKEY ORDER BY KEY_NAME").fetchall()
print(f"COUNT={len(rows)}")
for r in rows:
    print(f"{r['KEY_NAME']}|{r['KEY_SEQ_NUM']}")
