import argparse
import csv
import sqlite3
from datetime import datetime
from pathlib import Path


CHECKS = {
    'NO_PREDECESSOR': 'Actividad sin predecesora y no completada',
    'OVERDUE_MILESTONE': 'Milestone/LOE vencido y no completado',
    'TASK_WORK_MISMATCH_LABOR': 'Resumen TASK difiere de suma TASKRSRC labor',
    'COMPLETE_ZERO_ACT_WORK': 'Actividad completa con ACT_WORK_QTY=0',
    'COMPLETE_WITH_REMAIN_COST': 'Actividad completa con REMAIN_COST labor > 0',
}


def parse_args():
    p = argparse.ArgumentParser(description='Pilot audit for Primavera P6 Standalone SQLite')
    p.add_argument('--db', required=True, help='Path to PPMDBSQLite .db')
    p.add_argument('--out-dir', default='projects/P6-Standalone-Automation/data', help='Output folder')
    p.add_argument('--proj-id', type=int, default=None, help='Optional PROJ_ID filter')
    p.add_argument('--dry-run', action='store_true', help='No write-back actions (default behavior)')
    return p.parse_args()


def fetch_rows(cur, query, params):
    return [dict(r) for r in cur.execute(query, params).fetchall()]


def main():
    args = parse_args()
    db_path = Path(args.db)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    now = datetime.now()
    stamp = now.strftime('%Y%m%d_%H%M%S')

    con = sqlite3.connect(db_path)
    con.row_factory = sqlite3.Row
    cur = con.cursor()

    where_proj = ''
    params = []
    if args.proj_id is not None:
        where_proj = ' AND t.PROJ_ID = ?'
        params.append(args.proj_id)

    q_no_pred = f'''
    SELECT t.PROJ_ID, t.TASK_ID, t.TASK_CODE, t.TASK_NAME, t.STATUS_CODE, t.TASK_TYPE, t.TARGET_END_DATE
    FROM TASK t
    LEFT JOIN TASKPRED tp ON tp.TASK_ID = t.TASK_ID
    WHERE tp.TASK_ID IS NULL
      AND (t.STATUS_CODE IS NULL OR t.STATUS_CODE <> 'TK_Complete')
      {where_proj}
    ORDER BY t.PROJ_ID, t.TASK_CODE
    '''

    q_overdue_miles = f'''
    SELECT t.PROJ_ID, t.TASK_ID, t.TASK_CODE, t.TASK_NAME, t.STATUS_CODE, t.TASK_TYPE, t.TARGET_END_DATE
    FROM TASK t
    WHERE t.TASK_TYPE IN ('TT_Mile', 'TT_FinMile', 'TT_LOE')
      AND t.TARGET_END_DATE IS NOT NULL
      AND datetime(t.TARGET_END_DATE) < datetime('now','localtime')
      AND (t.STATUS_CODE IS NULL OR t.STATUS_CODE <> 'TK_Complete')
      {where_proj}
    ORDER BY t.PROJ_ID, t.TARGET_END_DATE
    '''

    q_task_work_mismatch = f'''
    SELECT
        t.PROJ_ID,
        t.TASK_ID,
        t.TASK_CODE,
        t.TASK_NAME,
        t.STATUS_CODE,
        ROUND(COALESCE(t.TARGET_WORK_QTY,0), 4) AS TARGET_WORK_QTY,
        ROUND(COALESCE(t.ACT_WORK_QTY,0), 4) AS ACT_WORK_QTY,
        ROUND(COALESCE(t.REMAIN_WORK_QTY,0), 4) AS REMAIN_WORK_QTY,
        ROUND(COALESCE(SUM(CASE WHEN tr.RSRC_TYPE='RT_Labor' THEN tr.TARGET_QTY ELSE 0 END),0), 4) AS TR_TARGET_QTY,
        ROUND(COALESCE(SUM(CASE WHEN tr.RSRC_TYPE='RT_Labor' THEN tr.ACT_REG_QTY ELSE 0 END),0), 4) AS TR_ACT_QTY,
        ROUND(COALESCE(SUM(CASE WHEN tr.RSRC_TYPE='RT_Labor' THEN tr.REMAIN_QTY ELSE 0 END),0), 4) AS TR_REMAIN_QTY
    FROM TASK t
    LEFT JOIN TASKRSRC tr ON tr.PROJ_ID=t.PROJ_ID AND tr.TASK_ID=t.TASK_ID
    WHERE 1=1 {where_proj}
    GROUP BY t.PROJ_ID, t.TASK_ID, t.TASK_CODE, t.TASK_NAME, t.STATUS_CODE, t.TARGET_WORK_QTY, t.ACT_WORK_QTY, t.REMAIN_WORK_QTY
    HAVING ABS(COALESCE(t.TARGET_WORK_QTY,0) - COALESCE(SUM(CASE WHEN tr.RSRC_TYPE='RT_Labor' THEN tr.TARGET_QTY ELSE 0 END),0)) > 0.01
        OR ABS(COALESCE(t.ACT_WORK_QTY,0) - COALESCE(SUM(CASE WHEN tr.RSRC_TYPE='RT_Labor' THEN tr.ACT_REG_QTY ELSE 0 END),0)) > 0.01
        OR ABS(COALESCE(t.REMAIN_WORK_QTY,0) - COALESCE(SUM(CASE WHEN tr.RSRC_TYPE='RT_Labor' THEN tr.REMAIN_QTY ELSE 0 END),0)) > 0.01
    ORDER BY t.PROJ_ID, t.TASK_CODE
    '''

    q_complete_zero_act = f'''
    SELECT t.PROJ_ID, t.TASK_ID, t.TASK_CODE, t.TASK_NAME, t.STATUS_CODE, ROUND(COALESCE(t.ACT_WORK_QTY,0), 4) AS ACT_WORK_QTY
    FROM TASK t
    WHERE t.STATUS_CODE = 'TK_Complete'
      AND COALESCE(t.ACT_WORK_QTY,0) = 0
      {where_proj}
    ORDER BY t.PROJ_ID, t.TASK_CODE
    '''

    q_complete_remain_cost = f'''
    SELECT
        t.PROJ_ID,
        t.TASK_ID,
        t.TASK_CODE,
        t.TASK_NAME,
        t.STATUS_CODE,
        ROUND(COALESCE(SUM(CASE WHEN tr.RSRC_TYPE='RT_Labor' THEN tr.REMAIN_COST ELSE 0 END),0), 4) AS REMAIN_COST
    FROM TASK t
    JOIN TASKRSRC tr ON tr.PROJ_ID=t.PROJ_ID AND tr.TASK_ID=t.TASK_ID
    WHERE t.STATUS_CODE = 'TK_Complete'
      {where_proj}
    GROUP BY t.PROJ_ID, t.TASK_ID, t.TASK_CODE, t.TASK_NAME, t.STATUS_CODE
    HAVING ROUND(COALESCE(SUM(CASE WHEN tr.RSRC_TYPE='RT_Labor' THEN tr.REMAIN_COST ELSE 0 END),0), 4) > 0
    ORDER BY t.PROJ_ID, t.TASK_CODE
    '''

    check_rows = {
        'NO_PREDECESSOR': fetch_rows(cur, q_no_pred, params),
        'OVERDUE_MILESTONE': fetch_rows(cur, q_overdue_miles, params),
        'TASK_WORK_MISMATCH_LABOR': fetch_rows(cur, q_task_work_mismatch, params),
        'COMPLETE_ZERO_ACT_WORK': fetch_rows(cur, q_complete_zero_act, params),
        'COMPLETE_WITH_REMAIN_COST': fetch_rows(cur, q_complete_remain_cost, params),
    }

    csv_path = out_dir / f'pilot_audit_{stamp}.csv'
    md_path = out_dir / f'pilot_audit_{stamp}.md'

    rows_for_csv = []
    all_fields = set(['check'])
    for check_name, rows in check_rows.items():
        for row in rows:
            out = {'check': check_name, **row}
            rows_for_csv.append(out)
            all_fields.update(out.keys())

    field_order = ['check', 'PROJ_ID', 'TASK_ID', 'TASK_CODE', 'TASK_NAME', 'STATUS_CODE', 'TASK_TYPE', 'TARGET_END_DATE', 'ACT_WORK_QTY', 'REMAIN_COST', 'TARGET_WORK_QTY', 'REMAIN_WORK_QTY', 'TR_TARGET_QTY', 'TR_ACT_QTY', 'TR_REMAIN_QTY']
    remaining = [f for f in sorted(all_fields) if f not in field_order]
    fields = field_order + remaining

    with csv_path.open('w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction='ignore')
        w.writeheader()
        for row in rows_for_csv:
            w.writerow(row)

    with md_path.open('w', encoding='utf-8') as f:
        f.write(f'# Pilot Audit P6 Standalone ({stamp})\n\n')
        f.write(f'- DB: `{db_path}`\n')
        f.write(f'- PROJ_ID filtro: `{args.proj_id}`\n')
        f.write(f'- Dry-run: `{True}`\n\n')
        f.write('## Resumen\n')
        for check_name, rows in check_rows.items():
            f.write(f'- {check_name}: **{len(rows)}** — {CHECKS[check_name]}\n')
        f.write(f'\nDetalle completo: `{csv_path}`\n')

    print(f'OK CSV={csv_path}')
    print(f'OK MD={md_path}')
    for check_name, rows in check_rows.items():
        print(f'{check_name}={len(rows)}')


if __name__ == '__main__':
    main()