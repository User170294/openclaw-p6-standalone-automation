import sqlite3
DB = r"C:\Users\josej\OneDrive\Documentos\PPMDBSQLite_20221109_BBDD_JJC_Rev B.db"
con = sqlite3.connect(DB)
cur = con.cursor()
for t in ["TRSRCFIN", "TRSRCSUM", "TRSRCFINCAT", "TASKRSRC", "TASK"]:
    try:
        cols = cur.execute(f"PRAGMA table_info({t})").fetchall()
    except Exception:
        cols = []
    print(f"--- {t} ({len(cols)}) ---")
    for c in cols:
        print(f"{c[1]}|{c[2]}")
con.close()
