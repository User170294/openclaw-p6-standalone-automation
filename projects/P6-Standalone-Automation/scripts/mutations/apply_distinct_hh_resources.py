import argparse
from pathlib import Path
import sys

SCRIPTS_ROOT = Path(__file__).resolve().parents[1]
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

from p6_utils import clone_resource_payload, get_next_id, now_str, open_db, set_next_id


def main():
    ap = argparse.ArgumentParser(description='Create distinct HH resources per task and reassign in one project')
    ap.add_argument('--db', required=True)
    ap.add_argument('--proj-id', type=int, required=True)
    ap.add_argument('--prefix', default='HH-1844')
    ap.add_argument('--apply', action='store_true')
    args = ap.parse_args()

    con = open_db(Path(args.db))
    cur = con.cursor()

    q = """
    SELECT t.TASK_ID, t.TASK_CODE, t.TASK_NAME,
           MIN(tr.RSRC_ID) AS OLD_RSRC_ID,
           COUNT(*) AS ASSIGN_COUNT
    FROM TASK t
    JOIN TASKRSRC tr ON tr.TASK_ID = t.TASK_ID
    WHERE t.PROJ_ID = ?
    GROUP BY t.TASK_ID, t.TASK_CODE, t.TASK_NAME
    ORDER BY t.TASK_CODE
    """
    tasks = cur.execute(q, (args.proj_id,)).fetchall()
    if not tasks:
        print('NO_TASK_ASSIGNMENTS_FOUND')
        return

    start_id = get_next_id(cur, 'rsrc_rsrc_id')
    print(f'TASKS_WITH_ASSIGNMENTS={len(tasks)}')
    print(f'NEXT_RSRC_START={start_id}')
    print(f"MODE={'APPLY' if args.apply else 'PLAN'}")

    plan_rows = []
    rsrc_id = start_id
    for t in tasks:
        task_code = (t['TASK_CODE'] or f"T{t['TASK_ID']}").strip()
        short = f"{args.prefix}-{task_code}"[:255]
        name = f"HH {task_code} - PROJ {args.proj_id}"[:255]
        plan_rows.append((t['TASK_ID'], t['TASK_CODE'], t['OLD_RSRC_ID'], rsrc_id, short, name))
        rsrc_id += 1

    for row in plan_rows[:10]:
        print(f'TASK_ID={row[0]}|TASK_CODE={row[1]}|OLD_RSRC={row[2]}|NEW_RSRC={row[3]}|SHORT={row[4]}')

    if not args.apply:
        con.close()
        return

    try:
        con.execute('BEGIN')
        inserted = 0
        reassigned_rows = 0

        for task_id, task_code, old_rsrc_id, new_rsrc_id, short, name in plan_rows:
            template = cur.execute('SELECT * FROM RSRC WHERE RSRC_ID=?', (old_rsrc_id,)).fetchone()
            if not template:
                template = cur.execute('SELECT * FROM RSRC WHERE RSRC_ID=9398').fetchone()
            payload = clone_resource_payload(template, new_rsrc_id, short, name, title='HH', rsrc_type=template['RSRC_TYPE'])
            cols = list(payload.keys())
            placeholders = ','.join(['?'] * len(cols))
            sql = f"INSERT INTO RSRC ({','.join(cols)}) VALUES ({placeholders})"
            cur.execute(sql, [payload[c] for c in cols])
            inserted += 1

            cur.execute(
                'UPDATE TASKRSRC SET RSRC_ID=?, UPDATE_DATE=?, UPDATE_USER=? WHERE TASK_ID=? AND PROJ_ID=?',
                (new_rsrc_id, now_str(), 'openclaw', task_id, args.proj_id),
            )
            reassigned_rows += cur.rowcount

            cur.execute(
                'UPDATE TASK SET RSRC_ID=?, UPDATE_DATE=?, UPDATE_USER=? WHERE TASK_ID=?',
                (new_rsrc_id, now_str(), 'openclaw', task_id),
            )

        set_next_id(cur, 'rsrc_rsrc_id', start_id + len(plan_rows))
        con.commit()
        print(f'INSERTED_RESOURCES={inserted}')
        print(f'REASSIGNED_TASKRSRC_ROWS={reassigned_rows}')
        print('COMMIT_OK')
    except Exception as e:
        con.rollback()
        print(f'ROLLBACK_ERROR={e}')
        raise
    finally:
        con.close()


if __name__ == '__main__':
    main()
