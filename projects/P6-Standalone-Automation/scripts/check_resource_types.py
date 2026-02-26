import sqlite3

DB = r"C:\Users\josej\OneDrive\Documentos\PPMDBSQLite_20221109_BBDD_JJC_Rev B - copia_WORK_20260226_145427.db"
con = sqlite3.connect(DB)
cur = con.cursor()
q = """
select RSRC_ID, RSRC_SHORT_NAME, RSRC_NAME, coalesce(RSRC_TYPE,''), coalesce(UNIT_ID,'')
from RSRC
where RSRC_SHORT_NAME like 'W153%OP%' or RSRC_ID in (9398,9399)
order by RSRC_ID
"""
for r in cur.execute(q):
    print("|".join(str(x) for x in r))
con.close()
