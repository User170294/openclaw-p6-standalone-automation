import sqlite3
from datetime import date, timedelta, datetime

DB = r"C:\Users\josej\OneDrive\Documentos\PPMDBSQLite_20221109_BBDD_JJC_Rev B.db"
PID = 26257
BPID = 26260
W08 = date(2026, 2, 16)

con = sqlite3.connect(DB)
con.row_factory = sqlite3.Row
cur = con.cursor()

metrics = {}
metrics['constraints'] = cur.execute(
    """SELECT COUNT(*) c FROM TASK
       WHERE PROJ_ID=?
         AND CSTR_TYPE IS NOT NULL
         AND TRIM(CSTR_TYPE)<>''""",
    (PID,),
).fetchone()['c']

metrics['invalid_dates'] = cur.execute(
    """SELECT COUNT(*) c FROM TASK
       WHERE PROJ_ID=?
         AND TARGET_START_DATE IS NOT NULL
         AND TARGET_END_DATE IS NOT NULL
         AND datetime(TARGET_END_DATE) < datetime(TARGET_START_DATE)""",
    (PID,),
).fetchone()['c']

metrics['no_pred_open'] = cur.execute(
    """SELECT COUNT(*) c
       FROM TASK t
       LEFT JOIN TASKPRED tp ON tp.TASK_ID=t.TASK_ID
       WHERE t.PROJ_ID=?
         AND tp.TASK_ID IS NULL
         AND COALESCE(t.STATUS_CODE,'') <> 'TK_Complete'""",
    (PID,),
).fetchone()['c']

metrics['no_succ_open'] = cur.execute(
    """SELECT COUNT(*) c
       FROM TASK t
       LEFT JOIN TASKPRED tp ON tp.PRED_TASK_ID=t.TASK_ID
       WHERE t.PROJ_ID=?
         AND tp.PRED_TASK_ID IS NULL
         AND COALESCE(t.STATUS_CODE,'') <> 'TK_Complete'""",
    (PID,),
).fetchone()['c']

metrics['neg_float'] = cur.execute(
    """SELECT COUNT(*) c FROM TASK
       WHERE PROJ_ID=?
         AND TOTAL_FLOAT_HR_CNT IS NOT NULL
         AND TOTAL_FLOAT_HR_CNT < 0""",
    (PID,),
).fetchone()['c']

s = cur.execute(
    """SELECT SUM(COALESCE(TARGET_WORK_QTY,0)) tgt,
              SUM(COALESCE(ACT_WORK_QTY,0)) act,
              SUM(COALESCE(REMAIN_WORK_QTY,0)) rem,
              COUNT(*) total,
              SUM(CASE WHEN STATUS_CODE='TK_Complete' THEN 1 ELSE 0 END) done,
              SUM(CASE WHEN STATUS_CODE='TK_Active' THEN 1 ELSE 0 END) active,
              SUM(CASE WHEN STATUS_CODE='TK_NotStart' THEN 1 ELSE 0 END) notstart
       FROM TASK WHERE PROJ_ID=?""",
    (PID,),
).fetchone()

rows = cur.execute(
    """SELECT TARGET_START_DATE, TARGET_END_DATE, COALESCE(TARGET_WORK_QTY,0) hh
       FROM TASK
       WHERE PROJ_ID=?
         AND TARGET_START_DATE IS NOT NULL
         AND TARGET_END_DATE IS NOT NULL
         AND COALESCE(TARGET_WORK_QTY,0) > 0""",
    (BPID,),
).fetchall()

byweek = {}
totalb = 0.0
for r in rows:
    sdt = datetime.strptime(r['TARGET_START_DATE'][:19], '%Y-%m-%d %H:%M:%S').date()
    edt = datetime.strptime(r['TARGET_END_DATE'][:19], '%Y-%m-%d %H:%M:%S').date()
    if edt < sdt:
        sdt, edt = edt, sdt
    hh = float(r['hh'] or 0.0)
    totalb += hh

    workdays = []
    d = sdt
    while d <= edt:
        if d.weekday() < 5:
            workdays.append(d)
        d += timedelta(days=1)
    if not workdays:
        workdays = [sdt]

    per = hh / len(workdays)
    for d in workdays:
        mon = d - timedelta(days=d.weekday())
        byweek[mon] = byweek.get(mon, 0.0) + per

base_cum = sum(v for k, v in byweek.items() if k <= W08)
base_pct = (base_cum / totalb * 100.0) if totalb else 0.0
real_pct = (float(s['act'] or 0.0) / float(s['tgt'] or 1.0) * 100.0) if float(s['tgt'] or 0.0) > 0 else 0.0

print('CHECK|VALUE')
for k, v in metrics.items():
    print(f"{k}|{v}")
print(f"target_hh|{float(s['tgt'] or 0):.3f}")
print(f"act_hh|{float(s['act'] or 0):.3f}")
print(f"remain_hh|{float(s['rem'] or 0):.3f}")
print(f"done_tasks|{int(s['done'] or 0)}/{int(s['total'] or 0)}")
print(f"active_tasks|{int(s['active'] or 0)}")
print(f"notstart_tasks|{int(s['notstart'] or 0)}")
print(f"real_pct_act_over_target|{real_pct:.2f}")
print(f"baseline_cum_w08_hh|{base_cum:.3f}")
print(f"baseline_cum_w08_pct|{base_pct:.2f}")
print(f"delta_pct_real_minus_base_w08|{(real_pct-base_pct):.2f}")

con.close()
