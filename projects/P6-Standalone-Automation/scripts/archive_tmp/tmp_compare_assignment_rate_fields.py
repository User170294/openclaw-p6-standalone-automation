import argparse
import sqlite3

ap = argparse.ArgumentParser()
ap.add_argument('--db', required=True)
ap.add_argument('--proj-a', type=int, required=True)
ap.add_argument('--proj-b', type=int, required=True)
args = ap.parse_args()

con = sqlite3.connect(args.db)
con.row_factory = sqlite3.Row
cur = con.cursor()

# Aggregate sensitive fields that affect spread/curves
for label, pid in [('A', args.proj_a), ('B', args.proj_b)]:
    r = cur.execute(
        '''
        SELECT COUNT(*) c,
               SUM(COALESCE(TARGET_QTY,0)) tq,
               SUM(COALESCE(TARGET_QTY_PER_HR,0)) tqph,
               SUM(COALESCE(REMAIN_QTY_PER_HR,0)) rqph,
               SUM(COALESCE(TARGET_COST,0)) tc,
               SUM(COALESCE(REMAIN_COST,0)) rc
        FROM TASKRSRC
        WHERE PROJ_ID=?
        ''',
        (pid,),
    ).fetchone()
    print(f"{label}|PROJ={pid}|ASG={r['c']}|TQ={r['tq'] or 0}|SUM_TQPH={r['tqph'] or 0}|SUM_RQPH={r['rqph'] or 0}|TC={r['tc'] or 0}|RC={r['rc'] or 0}")

# Compare first 5 matching task codes
q = '''
SELECT ta.TASK_CODE,
       SUM(COALESCE(ra.TARGET_QTY,0)) a_tq,
       SUM(COALESCE(ra.TARGET_QTY_PER_HR,0)) a_tqph,
       SUM(COALESCE(rb.TARGET_QTY,0)) b_tq,
       SUM(COALESCE(rb.TARGET_QTY_PER_HR,0)) b_tqph
FROM TASK ta
JOIN TASKRSRC ra ON ra.TASK_ID=ta.TASK_ID
JOIN TASK tb ON tb.TASK_CODE=ta.TASK_CODE AND tb.PROJ_ID=?
JOIN TASKRSRC rb ON rb.TASK_ID=tb.TASK_ID
WHERE ta.PROJ_ID=?
GROUP BY ta.TASK_CODE
ORDER BY ta.TASK_CODE
LIMIT 12
'''
for r in cur.execute(q, (args.proj_b, args.proj_a)).fetchall():
    print(f"TASK|{r['TASK_CODE']}|A_TQ={r['a_tq']}|A_TQPH={r['a_tqph']}|B_TQ={r['b_tq']}|B_TQPH={r['b_tqph']}")

con.close()
