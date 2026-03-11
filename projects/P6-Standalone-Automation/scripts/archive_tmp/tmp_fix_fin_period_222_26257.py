import shutil
import sqlite3
from pathlib import Path
from datetime import datetime

DB = Path(r"C:\Users\josej\OneDrive\Documentos\PPMDBSQLite_20221109_BBDD_JJC_Rev B.db")
PROJ_ID = 26262
FIN_DATES_ID = 222

stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
backup = DB.with_name(DB.stem + f".BACKUP_{stamp}" + DB.suffix)
shutil.copy2(DB, backup)
print(f"BACKUP={backup}")

con = sqlite3.connect(DB)
con.row_factory = sqlite3.Row
cur = con.cursor()

try:
    cur.execute("BEGIN")

    refs_proj = cur.execute(
        "SELECT COUNT(*) c FROM TRSRCFIN WHERE PROJ_ID=? AND FIN_DATES_ID=?",
        (PROJ_ID, FIN_DATES_ID),
    ).fetchone()["c"]
    refs_all = cur.execute(
        "SELECT COUNT(*) c FROM TRSRCFIN WHERE FIN_DATES_ID=?",
        (FIN_DATES_ID,),
    ).fetchone()["c"]
    print(f"TRSRCFIN_REFS_PROJ={refs_proj}")
    print(f"TRSRCFIN_REFS_ALL={refs_all}")

    cur.execute(
        "DELETE FROM TRSRCFIN WHERE PROJ_ID=? AND FIN_DATES_ID=?",
        (PROJ_ID, FIN_DATES_ID),
    )
    print(f"TRSRCFIN_DELETED={cur.rowcount}")

    refs_after_all = cur.execute(
        "SELECT COUNT(*) c FROM TRSRCFIN WHERE FIN_DATES_ID=?",
        (FIN_DATES_ID,),
    ).fetchone()["c"]
    print(f"TRSRCFIN_REFS_ALL_AFTER={refs_after_all}")

    findates_exists = cur.execute(
        "SELECT COUNT(*) c FROM FINDATES WHERE FIN_DATES_ID=?",
        (FIN_DATES_ID,),
    ).fetchone()["c"]

    # Delete FIN period only if now unreferenced
    deleted_findates = 0
    if refs_after_all == 0 and findates_exists:
        cur.execute("DELETE FROM FINDATES WHERE FIN_DATES_ID=?", (FIN_DATES_ID,))
        deleted_findates = cur.rowcount
    print(f"FINDATES_DELETED={deleted_findates}")

    con.commit()

except Exception as e:
    con.rollback()
    print(f"ERROR={e}")
    raise

finally:
    # post-check
    left_proj = cur.execute(
        "SELECT COUNT(*) c FROM TRSRCFIN WHERE PROJ_ID=?",
        (PROJ_ID,),
    ).fetchone()["c"]
    left_fin = cur.execute(
        "SELECT COUNT(*) c FROM TRSRCFIN WHERE FIN_DATES_ID=?",
        (FIN_DATES_ID,),
    ).fetchone()["c"]
    fin_row = cur.execute(
        "SELECT COUNT(*) c FROM FINDATES WHERE FIN_DATES_ID=?",
        (FIN_DATES_ID,),
    ).fetchone()["c"]
    print(f"POST_TRSRCFIN_PROJ_ROWS={left_proj}")
    print(f"POST_TRSRCFIN_FINID_ROWS={left_fin}")
    print(f"POST_FINDATES_EXISTS={fin_row}")
    con.close()
