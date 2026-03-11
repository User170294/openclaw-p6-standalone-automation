import argparse
import sqlite3
from pathlib import Path
from datetime import datetime


def build_resource_payload(template_row, new_rsrc_id, short_name, name):
    return {
        "RSRC_ID": new_rsrc_id,
        "PARENT_RSRC_ID": template_row["PARENT_RSRC_ID"],
        "CLNDR_ID": template_row["CLNDR_ID"],
        "ROLE_ID": template_row["ROLE_ID"],
        "SHIFT_ID": template_row["SHIFT_ID"],
        "USER_ID": None,
        "POBS_ID": template_row["POBS_ID"],
        "GUID": None,
        "RSRC_SEQ_NUM": None,
        "EMAIL_ADDR": None,
        "EMPLOYEE_CODE": None,
        "OFFICE_PHONE": None,
        "OTHER_PHONE": None,
        "RSRC_NAME": name,
        "RSRC_SHORT_NAME": short_name,
        "RSRC_TITLE_NAME": "HH",
        "DEF_QTY_PER_HR": template_row["DEF_QTY_PER_HR"],
        "COST_QTY_TYPE": template_row["COST_QTY_TYPE"],
        "OT_FACTOR": template_row["OT_FACTOR"],
        "ACTIVE_FLAG": "Y",
        "AUTO_COMPUTE_ACT_FLAG": template_row["AUTO_COMPUTE_ACT_FLAG"],
        "DEF_COST_QTY_LINK_FLAG": template_row["DEF_COST_QTY_LINK_FLAG"],
        "OT_FLAG": template_row["OT_FLAG"],
        "CURR_ID": template_row["CURR_ID"],
        "UNIT_ID": template_row["UNIT_ID"],
        "RSRC_TYPE": template_row["RSRC_TYPE"],
        "LOCATION_ID": template_row["LOCATION_ID"],
        "RSRC_NOTES": None,
        "TS_APPROVE_USER_ID": None,
        "TIMESHEET_FLAG": template_row["TIMESHEET_FLAG"],
        "CREATE_DATE": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "CREATE_USER": "openclaw",
        "UPDATE_DATE": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "UPDATE_USER": "openclaw",
        "DELETE_SESSION_ID": None,
        "DELETE_DATE": None,
    }


def main():
    ap = argparse.ArgumentParser(description="Create distinct HH resources per task and reassign in one project")
    ap.add_argument("--db", required=True)
    ap.add_argument("--proj-id", type=int, required=True)
    ap.add_argument("--prefix", default="HH-1844")
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    db = Path(args.db)
    con = sqlite3.connect(db)
    con.row_factory = sqlite3.Row
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
        print("NO_TASK_ASSIGNMENTS_FOUND")
        return

    next_rsrc = cur.execute("SELECT KEY_SEQ_NUM FROM NEXTKEY WHERE KEY_NAME='rsrc_rsrc_id'").fetchone()
    if not next_rsrc:
        raise RuntimeError("NEXTKEY rsrc_rsrc_id not found")

    start_id = int(next_rsrc["KEY_SEQ_NUM"])
    print(f"TASKS_WITH_ASSIGNMENTS={len(tasks)}")
    print(f"NEXT_RSRC_START={start_id}")
    print(f"MODE={'APPLY' if args.apply else 'PLAN'}")

    plan_rows = []
    rsrc_id = start_id
    for t in tasks:
        task_code = (t["TASK_CODE"] or f"T{t['TASK_ID']}").strip()
        short = f"{args.prefix}-{task_code}"[:255]
        name = f"HH {task_code} - PROJ {args.proj_id}"[:255]
        plan_rows.append((t["TASK_ID"], t["TASK_CODE"], t["OLD_RSRC_ID"], rsrc_id, short, name))
        rsrc_id += 1

    for row in plan_rows[:10]:
        print(f"TASK_ID={row[0]}|TASK_CODE={row[1]}|OLD_RSRC={row[2]}|NEW_RSRC={row[3]}|SHORT={row[4]}")

    if not args.apply:
        return

    try:
        con.execute("BEGIN")

        inserted = 0
        reassigned_rows = 0

        for task_id, task_code, old_rsrc_id, new_rsrc_id, short, name in plan_rows:
            template = cur.execute("SELECT * FROM RSRC WHERE RSRC_ID=?", (old_rsrc_id,)).fetchone()
            if not template:
                template = cur.execute("SELECT * FROM RSRC WHERE RSRC_ID=9398").fetchone()
            payload = build_resource_payload(template, new_rsrc_id, short, name)

            cols = list(payload.keys())
            placeholders = ",".join(["?"] * len(cols))
            sql = f"INSERT INTO RSRC ({','.join(cols)}) VALUES ({placeholders})"
            cur.execute(sql, [payload[c] for c in cols])
            inserted += 1

            cur.execute("UPDATE TASKRSRC SET RSRC_ID=?, UPDATE_DATE=?, UPDATE_USER=? WHERE TASK_ID=? AND PROJ_ID=?",
                        (new_rsrc_id, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "openclaw", task_id, args.proj_id))
            reassigned_rows += cur.rowcount

            cur.execute("UPDATE TASK SET RSRC_ID=?, UPDATE_DATE=?, UPDATE_USER=? WHERE TASK_ID=?",
                        (new_rsrc_id, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "openclaw", task_id))

        cur.execute("UPDATE NEXTKEY SET KEY_SEQ_NUM=?, UPDATE_DATE=?, UPDATE_USER=? WHERE KEY_NAME='rsrc_rsrc_id'",
                    (start_id + len(plan_rows), datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "openclaw"))

        con.commit()
        print(f"INSERTED_RESOURCES={inserted}")
        print(f"REASSIGNED_TASKRSRC_ROWS={reassigned_rows}")
        print("COMMIT_OK")
    except Exception as e:
        con.rollback()
        print(f"ROLLBACK_ERROR={e}")
        raise


if __name__ == "__main__":
    main()
