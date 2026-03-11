import argparse
import sqlite3
from datetime import datetime


def now():
    return datetime.now().strftime('%Y-%m-%d %H:%M:%S')


ap = argparse.ArgumentParser()
ap.add_argument('--db', required=True)
ap.add_argument('--proj-id', type=int, required=True)
ap.add_argument('--op-ids', required=True, help='CSV resource ids, ej: 9570,9571,9572')
ap.add_argument('--apply', action='store_true')
args = ap.parse_args()

op_ids = [int(x.strip()) for x in args.op_ids.split(',') if x.strip()]
if not op_ids:
    raise SystemExit('op-ids vacío')

con = sqlite3.connect(args.db)
con.row_factory = sqlite3.Row
cur = con.cursor()

marks = ','.join(['?'] * len(op_ids))
params = [args.proj_id] + op_ids

before = cur.execute(
    f"""
    SELECT COUNT(*) c,
           SUM(COALESCE(TARGET_QTY_PER_HR,0)) tqph,
           SUM(COALESCE(REMAIN_QTY_PER_HR,0)) rqph
    FROM TASKRSRC
    WHERE PROJ_ID=? AND RSRC_ID IN ({marks})
    """,
    params,
).fetchone()

print(f"PROJ_ID={args.proj_id}")
print(f"OP_IDS={op_ids}")
print(f"BEFORE|ROWS={before['c'] or 0}|SUM_TQPH={before['tqph'] or 0}|SUM_RQPH={before['rqph'] or 0}")
print(f"MODE={'APPLY' if args.apply else 'PLAN'}")

if args.apply:
    cur.execute(
        f"""
        UPDATE TASKRSRC
        SET TARGET_QTY_PER_HR = ROUND(COALESCE(TARGET_QTY_PER_HR,0)/3.0, 6),
            REMAIN_QTY_PER_HR = ROUND(COALESCE(REMAIN_QTY_PER_HR,0)/3.0, 6),
            UPDATE_DATE = ?,
            UPDATE_USER = 'openclaw'
        WHERE PROJ_ID=? AND RSRC_ID IN ({marks})
        """,
        [now(), args.proj_id] + op_ids,
    )
    updated = cur.rowcount
    con.commit()

    after = cur.execute(
        f"""
        SELECT COUNT(*) c,
               SUM(COALESCE(TARGET_QTY_PER_HR,0)) tqph,
               SUM(COALESCE(REMAIN_QTY_PER_HR,0)) rqph
        FROM TASKRSRC
        WHERE PROJ_ID=? AND RSRC_ID IN ({marks})
        """,
        params,
    ).fetchone()

    print(f"UPDATED_ROWS={updated}")
    print(f"AFTER|ROWS={after['c'] or 0}|SUM_TQPH={after['tqph'] or 0}|SUM_RQPH={after['rqph'] or 0}")
    print('COMMIT_OK')

con.close()
