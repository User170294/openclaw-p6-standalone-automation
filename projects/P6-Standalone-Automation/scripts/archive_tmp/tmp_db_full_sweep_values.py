import sqlite3
import math

DB = r"C:\Users\josej\OneDrive\Documentos\PPMDBSQLite_20221109_BBDD_JJC_Rev B.db"
TARGETS = [1377.34, 2455.54, 1078.2, 7021.8]
TOL = 0.01

con = sqlite3.connect(DB)
con.row_factory = sqlite3.Row
cur = con.cursor()

tables = [r['name'] for r in cur.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name").fetchall()]
print(f"TABLES={len(tables)}")

hits = []

for t in tables:
    try:
        cols = cur.execute(f"PRAGMA table_info({t})").fetchall()
    except Exception:
        continue
    num_cols = [c['name'] for c in cols if (c['type'] or '').upper() in ('REAL','FLOAT','DOUBLE','NUMERIC','DECIMAL','INTEGER')]
    text_cols = [c['name'] for c in cols if 'TEXT' in (c['type'] or '').upper()]

    # Numeric exact/near hits
    for c in num_cols:
        for v in TARGETS:
            try:
                q = f"SELECT COUNT(*) c FROM {t} WHERE {c} IS NOT NULL AND ABS(CAST({c} AS REAL) - ?) <= ?"
                n = cur.execute(q, (v, TOL)).fetchone()['c']
                if n and n > 0:
                    hits.append((t, c, 'NUM', v, n))
            except Exception:
                pass

    # Text contains literal values (for curve strings etc.)
    for c in text_cols:
        for v in TARGETS:
            s = f"{v}"
            try:
                q = f"SELECT COUNT(*) c FROM {t} WHERE {c} LIKE ?"
                n = cur.execute(q, (f"%{s}%",)).fetchone()['c']
                if n and n > 0:
                    hits.append((t, c, 'TEXT', s, n))
            except Exception:
                pass

print(f"HITS={len(hits)}")
for h in hits:
    print(f"{h[0]}|{h[1]}|{h[2]}|{h[3]}|count={h[4]}")

# Print sample rows for most relevant hits
print("SAMPLES_START")
for t,c,kind,v,n in hits[:30]:
    try:
        if kind == 'NUM':
            q = f"SELECT * FROM {t} WHERE {c} IS NOT NULL AND ABS(CAST({c} AS REAL)-?)<=? LIMIT 3"
            rows = cur.execute(q, (float(v), TOL)).fetchall()
        else:
            q = f"SELECT * FROM {t} WHERE {c} LIKE ? LIMIT 3"
            rows = cur.execute(q, (f"%{v}%",)).fetchall()
        for r in rows:
            d = dict(r)
            # compact print
            print(f"{t}|{c}|{kind}|{v}|ROW|" + str({k:d[k] for k in list(d.keys())[:12]}))
    except Exception:
        pass
print("SAMPLES_END")

con.close()
