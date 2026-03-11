import argparse
import sqlite3
from collections import defaultdict

ap = argparse.ArgumentParser()
ap.add_argument('--db', required=True)
ap.add_argument('--proj-a', type=int, required=True)
ap.add_argument('--proj-b', type=int, required=True)
args = ap.parse_args()

con = sqlite3.connect(args.db)
con.row_factory = sqlite3.Row
cur = con.cursor()

def proj_name(pid):
    r = cur.execute('SELECT PROJ_SHORT_NAME FROM PROJECT WHERE PROJ_ID=?', (pid,)).fetchone()
    return r['PROJ_SHORT_NAME'] if r else f'PROJ_{pid}'

def summary(pid):
    r = cur.execute(
        '''
        SELECT COUNT(*) AS asg,
               COUNT(DISTINCT RSRC_ID) AS rsrc,
               SUM(COALESCE(TARGET_QTY,0)) AS tq,
               SUM(COALESCE(REMAIN_QTY,0)) AS rq,
               SUM(COALESCE(ACT_REG_QTY,0)+COALESCE(ACT_OT_QTY,0)) AS aq
        FROM TASKRSRC
        WHERE PROJ_ID=?
        ''',
        (pid,),
    ).fetchone()
    return r

def by_resource(pid):
    rows = cur.execute(
        '''
        SELECT tr.RSRC_ID,
               COALESCE(r.RSRC_SHORT_NAME,'') AS short,
               COALESCE(r.RSRC_NAME,'') AS name,
               COUNT(*) AS asg,
               SUM(COALESCE(tr.TARGET_QTY,0)) AS tq
        FROM TASKRSRC tr
        LEFT JOIN RSRC r ON r.RSRC_ID=tr.RSRC_ID
        WHERE tr.PROJ_ID=?
        GROUP BY tr.RSRC_ID, r.RSRC_SHORT_NAME, r.RSRC_NAME
        ORDER BY tq DESC
        ''',
        (pid,),
    ).fetchall()
    return rows

def task_totals(pid):
    rows = cur.execute(
        '''
        SELECT t.TASK_CODE,
               SUM(COALESCE(tr.TARGET_QTY,0)) AS tq,
               COUNT(*) AS asg
        FROM TASK t
        JOIN TASKRSRC tr ON tr.TASK_ID=t.TASK_ID
        WHERE t.PROJ_ID=?
        GROUP BY t.TASK_CODE
        ''',
        (pid,),
    ).fetchall()
    d = {r['TASK_CODE']: (float(r['tq'] or 0), int(r['asg'])) for r in rows}
    return d

name_a = proj_name(args.proj_a)
name_b = proj_name(args.proj_b)

s_a = summary(args.proj_a)
s_b = summary(args.proj_b)

print(f"A={args.proj_a}|{name_a}")
print(f"B={args.proj_b}|{name_b}")
print('--- SUMMARY ---')
print(f"A|ASSIGN={s_a['asg']}|RSRC={s_a['rsrc']}|TARGET_HH={s_a['tq'] or 0}|REMAIN_HH={s_a['rq'] or 0}|ACT_HH={s_a['aq'] or 0}")
print(f"B|ASSIGN={s_b['asg']}|RSRC={s_b['rsrc']}|TARGET_HH={s_b['tq'] or 0}|REMAIN_HH={s_b['rq'] or 0}|ACT_HH={s_b['aq'] or 0}")
print(f"DELTA_A-B|ASSIGN={(s_a['asg'] or 0)-(s_b['asg'] or 0)}|TARGET_HH={(s_a['tq'] or 0)-(s_b['tq'] or 0)}")

print('--- BY RESOURCE (A) ---')
for r in by_resource(args.proj_a):
    print(f"A_RSRC|{r['RSRC_ID']}|{r['short']}|{r['name']}|ASG={r['asg']}|TGT_HH={r['tq'] or 0}")

print('--- BY RESOURCE (B) ---')
for r in by_resource(args.proj_b):
    print(f"B_RSRC|{r['RSRC_ID']}|{r['short']}|{r['name']}|ASG={r['asg']}|TGT_HH={r['tq'] or 0}")

print('--- TASK HH CONSISTENCY ---')
ta = task_totals(args.proj_a)
tb = task_totals(args.proj_b)
all_codes = sorted(set(ta.keys()) | set(tb.keys()))

diff_count = 0
for c in all_codes:
    a_tq, a_asg = ta.get(c, (0.0, 0))
    b_tq, b_asg = tb.get(c, (0.0, 0))
    if round(a_tq - b_tq, 4) != 0 or a_asg != b_asg:
        diff_count += 1
        print(f"TASK_DIFF|{c}|A_HH={a_tq}|B_HH={b_tq}|A_ASG={a_asg}|B_ASG={b_asg}")

print(f"TASK_DIFF_COUNT={diff_count}")

con.close()
