import sqlite3
DB = r"C:\Users\josej\OneDrive\Documentos\PPMDBSQLite_20221109_BBDD_JJC_Rev B.db"
con = sqlite3.connect(DB)
cur = con.cursor()
for c in cur.execute("PRAGMA table_info(TASKRSRC)").fetchall():
    print(f"{c[1]}|{c[2]}")
con.close()
