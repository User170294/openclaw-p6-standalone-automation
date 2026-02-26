import argparse
import sqlite3
from pathlib import Path
from datetime import datetime


def now_str():
    return datetime.now().strftime('%Y-%m-%d %H:%M:%S')


def get_next_id(cur, key_name):
    row = cur.execute("SELECT KEY_SEQ_NUM FROM NEXTKEY WHERE KEY_NAME=?", (key_name,)).fetchone()
    if not row:
        raise RuntimeError(f"NEXTKEY {key_name} not found")
    return int(row[0])


def set_next_id(cur, key_name, value):
    cur.execute(
        "UPDATE NEXTKEY SET KEY_SEQ_NUM=?, UPDATE_DATE=?, UPDATE_USER=? WHERE KEY_NAME=?",
        (value, now_str(), 'openclaw', key_name),
    )


def clone_resource_payload(template, rsrc_id, short_name, name):
    return {
        "RSRC_ID": rsrc_id,
        "PARENT_RSRC_ID": template["PARENT_RSRC_ID"],
        "CLNDR_ID": template["CLNDR_ID"],
        "ROLE_ID": template["ROLE_ID"],
        "SHIFT_ID": template["SHIFT_ID"],
        "USER_ID": None,
        "POBS_ID": template["POBS_ID"],
        "GUID": None,
        "RSRC_SEQ_NUM": None,
        "EMAIL_ADDR": None,
        "EMPLOYEE_CODE": None,
        "OFFICE_PHONE": None,
        "OTHER_PHONE": None,
        "RSRC_NAME": name,
        "RSRC_SHORT_NAME": short_name,
        "RSRC_TITLE_NAME": "CUADRILLA",
        "DEF_QTY_PER_HR": template["DEF_QTY_PER_HR"],
        "COST_QTY_TYPE": template["COST_QTY_TYPE"],
        "OT_FACTOR": template["OT_FACTOR"],
        "ACTIVE_FLAG": "Y",
        "AUTO_COMPUTE_ACT_FLAG": template["AUTO_COMPUTE_ACT_FLAG"],
        "DEF_COST_QTY_LINK_FLAG": template["DEF_COST_QTY_LINK_FLAG"],
        "OT_FLAG": template["OT_FLAG"],
        "CURR_ID": template["CURR_ID"],
        "UNIT_ID": template["UNIT_ID"],
        "RSRC_TYPE": template["RSRC_TYPE"],
        "LOCATION_ID": template["LOCATION_ID"],
        "RSRC_NOTES": None,
        "TS_APPROVE_USER_ID": None,
        "TIMESHEET_FLAG": template["TIMESHEET_FLAG"],
        "CREATE_DATE": now_str(),
        "CREATE_USER": "openclaw",
        "UPDATE_DATE": now_str(),
        "UPDATE_USER": "openclaw",
        "DELETE_SESSION_ID": None,
        "DELETE_DATE": None,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--db', required=True)
    ap.add_argument('--proj-id', type=int, required=True)
    ap.add_argument('--wbs-id', type=int, required=True)
    ap.add_argument('--apply', action='store_true')
    args = ap.parse_args()

    con = sqlite3.connect(Path(args.db))
    con.row_factory = sqlite3.Row
    cur = con.cursor()

    tasks = cur.execute(
        """
        WITH RECURSIVE wbs_tree AS (
          SELECT WBS_ID FROM PROJWBS WHERE PROJ_ID=? AND WBS_ID=?
          UNION ALL
          SELECT c.WBS_ID
          FROM PROJWBS c
          JOIN wbs_tree p ON c.PARENT_WBS_ID = p.WBS_ID
          WHERE c.PROJ_ID=?
        )
        SELECT t.TASK_ID, t.TASK_CODE, t.TASK_NAME
        FROM TASK t
        WHERE t.PROJ_ID=? AND t.WBS_ID IN (SELECT WBS_ID FROM wbs_tree)
        ORDER BY t.TASK_CODE
        """,
        (args.proj_id, args.wbs_id, args.proj_id, args.proj_id),
    ).fetchall()

    if not tasks:
        print('NO_TASKS_IN_WBS')
        return

    # Find a template resource from first existing assignment in that WBS
    template = cur.execute(
        """
        WITH RECURSIVE wbs_tree AS (
          SELECT WBS_ID FROM PROJWBS WHERE PROJ_ID=? AND WBS_ID=?
          UNION ALL
          SELECT c.WBS_ID
          FROM PROJWBS c
          JOIN wbs_tree p ON c.PARENT_WBS_ID = p.WBS_ID
          WHERE c.PROJ_ID=?
        )
        SELECT r.*
        FROM TASKRSRC tr
        JOIN TASK t ON t.TASK_ID = tr.TASK_ID
        JOIN RSRC r ON r.RSRC_ID = tr.RSRC_ID
        WHERE t.PROJ_ID=? AND t.WBS_ID IN (SELECT WBS_ID FROM wbs_tree)
        LIMIT 1
        """,
        (args.proj_id, args.wbs_id, args.proj_id, args.proj_id),
    ).fetchone()
    if not template:
        raise RuntimeError('No existing assignment template found in WBS')

    next_rsrc = get_next_id(cur, 'rsrc_rsrc_id')
    next_taskrsrc = get_next_id(cur, 'taskrsrc_taskrsrc_id')

    crew_defs = [
        ('OP1', 'Operador 1'),
        ('OP2', 'Operador 2'),
        ('OP3', 'Operador 3'),
    ]

    # plan
    print(f"TASKS={len(tasks)}")
    print(f"CREW_RESOURCES=3")
    print(f"MODE={'APPLY' if args.apply else 'PLAN'}")

    if not args.apply:
        return

    con.execute('BEGIN')
    try:
        # create 3 crew resources specific to this WBS
        crew_ids = []
        for code, label in crew_defs:
            rid = next_rsrc
            next_rsrc += 1
            short = f"W{args.wbs_id}-{code}"
            name = f"Cuadrilla WBS {args.wbs_id} - {label}"
            payload = clone_resource_payload(template, rid, short, name)
            cols = list(payload.keys())
            cur.execute(
                f"INSERT INTO RSRC ({','.join(cols)}) VALUES ({','.join(['?']*len(cols))})",
                [payload[c] for c in cols],
            )
            crew_ids.append(rid)

        created_assign = 0
        updated_tasks = 0

        for t in tasks:
            task_id = t['TASK_ID']
            # sum HH existing in task (TARGET_QTY/REMAIN_QTY + ACT)
            old = cur.execute(
                """
                SELECT
                  COALESCE(SUM(TARGET_QTY),0) AS target_qty,
                  COALESCE(SUM(REMAIN_QTY),0) AS remain_qty,
                  COALESCE(SUM(ACT_REG_QTY),0) + COALESCE(SUM(ACT_OT_QTY),0) AS act_qty,
                  COALESCE(SUM(TARGET_COST),0) AS target_cost
                FROM TASKRSRC
                WHERE TASK_ID=? AND PROJ_ID=?
                """,
                (task_id, args.proj_id),
            ).fetchone()

            # delete current assignments for that task
            cur.execute("DELETE FROM TASKRSRC WHERE TASK_ID=? AND PROJ_ID=?", (task_id, args.proj_id))

            tq = float(old['target_qty'])
            rq = float(old['remain_qty'])
            aq = float(old['act_qty'])
            tc = float(old['target_cost'])

            splits = []
            for i in range(3):
                if i < 2:
                    splits.append((round(tq/3.0, 4), round(rq/3.0, 4), round(aq/3.0, 4), round(tc/3.0, 4)))
                else:
                    # force exact sum on last row
                    stq = round(tq - splits[0][0] - splits[1][0], 4)
                    srq = round(rq - splits[0][1] - splits[1][1], 4)
                    saq = round(aq - splits[0][2] - splits[1][2], 4)
                    stc = round(tc - splits[0][3] - splits[1][3], 4)
                    splits.append((stq, srq, saq, stc))

            for idx, rid in enumerate(crew_ids):
                trid = next_taskrsrc
                next_taskrsrc += 1
                stq, srq, saq, stc = splits[idx]
                act_reg = saq
                act_ot = 0.0

                cur.execute(
                    """
                    INSERT INTO TASKRSRC (
                      TASKRSRC_ID, TASK_ID, PROJ_ID, RSRC_ID,
                      TARGET_QTY, REMAIN_QTY, ACT_REG_QTY, ACT_OT_QTY, TARGET_COST,
                      CREATE_DATE, CREATE_USER, UPDATE_DATE, UPDATE_USER
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        trid, task_id, args.proj_id, rid,
                        stq, srq, act_reg, act_ot, stc,
                        now_str(), 'openclaw', now_str(), 'openclaw'
                    ),
                )
                created_assign += 1

            # keep TASK.RSRC_ID pointed to operador 1
            cur.execute(
                "UPDATE TASK SET RSRC_ID=?, UPDATE_DATE=?, UPDATE_USER=? WHERE TASK_ID=?",
                (crew_ids[0], now_str(), 'openclaw', task_id),
            )
            updated_tasks += 1

        set_next_id(cur, 'rsrc_rsrc_id', next_rsrc)
        set_next_id(cur, 'taskrsrc_taskrsrc_id', next_taskrsrc)

        con.commit()
        print(f"CREATED_CREW_RESOURCES={len(crew_ids)}")
        print(f"CREATED_TASKRSRC_ROWS={created_assign}")
        print(f"UPDATED_TASKS={updated_tasks}")
        print('COMMIT_OK')
    except Exception as e:
        con.rollback()
        print(f"ROLLBACK_ERROR={e}")
        raise


if __name__ == '__main__':
    main()
