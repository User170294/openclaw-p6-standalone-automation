import sqlite3
DB=r"C:\Users\josej\OneDrive\Documentos\PPMDBSQLite_20221109_BBDD_JJC_Rev B - copia.db"
con=sqlite3.connect(DB)
cur=con.cursor()
print(cur.execute("select WBS_ID, WBS_SHORT_NAME, WBS_NAME, PROJ_ID, PARENT_WBS_ID from PROJWBS where WBS_ID=154616").fetchall())
print(cur.execute("select PROJ_ID, PROJ_SHORT_NAME from PROJECT where PROJ_ID=26260").fetchall())
con.close()
