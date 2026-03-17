import argparse
from pathlib import Path
import sys

SCRIPTS_ROOT = Path(__file__).resolve().parents[1]
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

from p6_utils import clone_resource_payload, get_next_id, insert_row, now_str, open_db, set_next_id, split3


def clone_resource_row(template, new_id, short_name, name):
    return clone_resource_payload(template, new_id, short_name, name, rsrc_type='RT_Labor')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--db', required=True)
    ap.add_argument('--proj-id', type=int, required=True)
    ap.add_argument('--old-rsrc', type=int, required=True)
    ap.add_argument('--apply', action='store_true')
    args = ap.parse_args()

    con = open_db(Path(args.db))
    cur = con.cursor()

    old = cur.execute('SELECT * FROM RSRC WHERE RSRC_ID=?', (args.old_rsrc,)).fetchone()
    if not old:
        raise RuntimeError(f"RSRC {args.old_rsrc} no existe")

    asg = cur.execute(
        'SELECT * FROM TASKRSRC WHERE PROJ_ID=? AND RSRC_ID=? ORDER BY TASKRSRC_ID',
        (args.proj_id, args.old_rsrc),
    ).fetchall()

    if not asg:
        print('NO_ASSIGNMENTS_FOUND')
        return

    sum_old = cur.execute(
        """
        SELECT COUNT(*) c,
               SUM(COALESCE(TARGET_QTY,0)) tq,
               SUM(COALESCE(REMAIN_QTY,0)) rq,
               SUM(COALESCE(ACT_REG_QTY,0)+COALESCE(ACT_OT_QTY,0)) aq
        FROM TASKRSRC
        WHERE PROJ_ID=? AND RSRC_ID=?
        """,
        (args.proj_id, args.old_rsrc),
    ).fetchone()

    next_rsrc = get_next_id(cur, 'rsrc_rsrc_id')
    next_taskrsrc = get_next_id(cur, 'taskrsrc_taskrsrc_id')

    print(f"PROJ_ID={args.proj_id}")
    print(f"OLD_RSRC={args.old_rsrc}")
    print(f"ASSIGNMENTS_OLD={sum_old['c']}")
    print(f"OLD_TOTAL_HH_TARGET={sum_old['tq'] or 0}")
    print(f"MODE={'APPLY' if args.apply else 'PLAN'}")

    op_defs = [
        (next_rsrc, 'OP1', 'OP1'),
        (next_rsrc + 1, 'OP2', 'OP2'),
        (next_rsrc + 2, 'OP3', 'OP3'),
    ]

    for rid, s, n in op_defs:
        print(f"NEW_RSRC_PLAN|{rid}|{s}|{n}")

    if not args.apply:
        con.close()
        return

    try:
        con.execute('BEGIN')

        # Create OP1/OP2/OP3
        for rid, short, name in op_defs:
            payload = clone_resource_row(old, rid, short, name)
            insert_row(cur, 'RSRC', payload)

        op1, op2, op3 = op_defs[0][0], op_defs[1][0], op_defs[2][0]

        created_new_assignments = 0
        updated_original_assignments = 0

        # Reassign each existing assignment: keep row as OP1 and add OP2/OP3 with split HH
        for r in asg:
            row = dict(r)

            tq = float(row.get('TARGET_QTY') or 0.0)
            rq = float(row.get('REMAIN_QTY') or 0.0)
            ar = float(row.get('ACT_REG_QTY') or 0.0)
            ao = float(row.get('ACT_OT_QTY') or 0.0)

            tq_s = split3(tq)
            rq_s = split3(rq)
            ar_s = split3(ar)
            ao_s = split3(ao)

            # update original row => OP1
            cur.execute(
                """
                UPDATE TASKRSRC
                SET RSRC_ID=?,
                    TARGET_QTY=?, REMAIN_QTY=?, ACT_REG_QTY=?, ACT_OT_QTY=?,
                    COST_PER_QTY=?,
                    TARGET_COST=?, REMAIN_COST=?, ACT_REG_COST=?, ACT_OT_COST=?,
                    RSRC_TYPE='RT_Labor',
                    UPDATE_DATE=?, UPDATE_USER=?
                WHERE TASKRSRC_ID=?
                """,
                (
                    op1,
                    tq_s[0], rq_s[0], ar_s[0], ao_s[0],
                    1.0,
                    round(tq_s[0] * 1.0, 4),
                    round(rq_s[0] * 1.0, 4),
                    round(ar_s[0] * 1.0, 4),
                    round(ao_s[0] * 1.0, 4),
                    now_str(), 'openclaw', row['TASKRSRC_ID']
                )
            )
            updated_original_assignments += 1

            # insert OP2 and OP3 copies
            for idx, new_rsrc in enumerate([op2, op3], start=1):
                new_row = dict(row)
                new_row['TASKRSRC_ID'] = next_taskrsrc
                next_taskrsrc += 1
                new_row['RSRC_ID'] = new_rsrc
                new_row['TARGET_QTY'] = tq_s[idx]
                new_row['REMAIN_QTY'] = rq_s[idx]
                new_row['ACT_REG_QTY'] = ar_s[idx]
                new_row['ACT_OT_QTY'] = ao_s[idx]
                new_row['COST_PER_QTY'] = 1.0
                new_row['TARGET_COST'] = round(tq_s[idx] * 1.0, 4)
                new_row['REMAIN_COST'] = round(rq_s[idx] * 1.0, 4)
                new_row['ACT_REG_COST'] = round(ar_s[idx] * 1.0, 4)
                new_row['ACT_OT_COST'] = round(ao_s[idx] * 1.0, 4)
                new_row['RSRC_TYPE'] = 'RT_Labor'
                new_row['GUID'] = None
                new_row['CREATE_DATE'] = now_str()
                new_row['CREATE_USER'] = 'openclaw'
                new_row['UPDATE_DATE'] = now_str()
                new_row['UPDATE_USER'] = 'openclaw'
                new_row['DELETE_SESSION_ID'] = None
                new_row['DELETE_DATE'] = None
                insert_row(cur, 'TASKRSRC', new_row)
                created_new_assignments += 1

        # Update TASK master pointer where it used old resource
        cur.execute(
            "UPDATE TASK SET RSRC_ID=?, UPDATE_DATE=?, UPDATE_USER=? WHERE PROJ_ID=? AND RSRC_ID=?",
            (op1, now_str(), 'openclaw', args.proj_id, args.old_rsrc)
        )
        updated_tasks = cur.rowcount

        # Update NEXTKEY
        set_next_id(cur, 'rsrc_rsrc_id', next_rsrc + 3)
        set_next_id(cur, 'taskrsrc_taskrsrc_id', next_taskrsrc)

        # Delete old RSRC if no more references in TASKRSRC/TASK
        refs_taskrsrc = cur.execute('SELECT COUNT(*) FROM TASKRSRC WHERE RSRC_ID=?', (args.old_rsrc,)).fetchone()[0]
        refs_task = cur.execute('SELECT COUNT(*) FROM TASK WHERE RSRC_ID=?', (args.old_rsrc,)).fetchone()[0]
        deleted_old = 0
        if refs_taskrsrc == 0 and refs_task == 0:
            cur.execute('DELETE FROM RSRC WHERE RSRC_ID=?', (args.old_rsrc,))
            deleted_old = cur.rowcount

        con.commit()

        sum_new = cur.execute(
            """
            SELECT COUNT(*) c,
                   COUNT(DISTINCT RSRC_ID) d,
                   SUM(COALESCE(TARGET_QTY,0)) tq
            FROM TASKRSRC
            WHERE PROJ_ID=? AND RSRC_ID IN (?,?,?)
            """,
            (args.proj_id, op1, op2, op3),
        ).fetchone()

        print(f"CREATED_RESOURCES=3")
        print(f"UPDATED_OLD_ASSIGNMENTS={updated_original_assignments}")
        print(f"CREATED_NEW_ASSIGNMENTS={created_new_assignments}")
        print(f"UPDATED_TASKS={updated_tasks}")
        print(f"OLD_RESOURCE_DELETED={deleted_old}")
        print(f"NEW_ASSIGNMENTS={sum_new['c']}|NEW_DISTINCT_RSRC={sum_new['d']}|NEW_TOTAL_HH_TARGET={sum_new['tq'] or 0}")
        print('COMMIT_OK')
    except Exception as e:
        con.rollback()
        print(f'ROLLBACK_ERROR={e}')
        raise
    finally:
        con.close()


if __name__ == '__main__':
    main()
