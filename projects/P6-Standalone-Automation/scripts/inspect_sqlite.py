import sqlite3
from pathlib import Path

DB_PATH = Path(r"C:\Users\josej\OneDrive\Documentos\PPMDBSQLite_20221109_BBDD_JJC_Rev B - copia.db")

con = sqlite3.connect(DB_PATH)
cur = con.cursor()
cur.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
tables = [r[0] for r in cur.fetchall()]
print(f"TABLE_COUNT={len(tables)}")
for name in tables[:40]:
    print(name)

print("\n--- TASK columns ---")
cur.execute("PRAGMA table_info(TASK)")
for col in cur.fetchall():
    print(f"{col[1]}|{col[2]}")

print("\n--- TASKPRED columns ---")
cur.execute("PRAGMA table_info(TASKPRED)")
for col in cur.fetchall():
    print(f"{col[1]}|{col[2]}")
