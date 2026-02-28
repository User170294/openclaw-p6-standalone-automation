import sqlite3

db = r"C:\Users\josej\OneDrive\Documentos\PPMDBSQLite_20221109_BBDD_JJC_Rev B.db"
con = sqlite3.connect(db)
cur = con.cursor()
for row in cur.execute("PRAGMA table_info(TASK)").fetchall():
    print(row[1])
con.close()
