import argparse
from pathlib import Path
import sys

SCRIPTS_ROOT = Path(__file__).resolve().parents[1]
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

from p6_utils import get_next_id, now_str, open_db, set_next_id


def main():
    ap = argparse.ArgumentParser(description='Create project under Simtexx root in P6 SQLite')
    ap.add_argument('--db', required=True)
    ap.add_argument('--parent-wbs-id', type=int, default=151785)
    ap.add_argument('--template-proj-id', type=int, default=26196)
    ap.add_argument('--new-short', required=True)
    ap.add_argument('--new-name', required=True)
    ap.add_argument('--new-start', required=True)
    ap.add_argument('--apply', action='store_true')
    args = ap.parse_args()

    con = open_db(args.db)
    cur = con.cursor()

    exists = cur.execute('SELECT PROJ_ID, PROJ_SHORT_NAME FROM PROJECT WHERE PROJ_SHORT_NAME=?', (args.new_short,)).fetchall()
    if exists:
        print(f'ALREADY_EXISTS={exists}')
        con.close()
        raise SystemExit(1)

    proj_id = get_next_id(cur, 'project_proj_id')
    wbs_id = get_next_id(cur, 'projwbs_wbs_id')
    seq = cur.execute('SELECT COALESCE(MAX(SEQ_NUM),0)+1 FROM PROJWBS WHERE PARENT_WBS_ID=?', (args.parent_wbs_id,)).fetchone()[0]

    print(f'PLAN|PROJ_ID={proj_id}|WBS_ID={wbs_id}|SEQ={seq}|MODE={'APPLY' if args.apply else 'PLAN'}')
    if not args.apply:
        con.close()
        return

    con.execute('BEGIN')
    try:
        cur.execute(
            """
            INSERT INTO PROJECT (
              PROJ_ID,FY_START_MONTH_NUM,RSRC_SELF_ADD_FLAG,ALLOW_COMPLETE_FLAG,RSRC_MULTI_ASSIGN_FLAG,CHECKOUT_FLAG,PROJECT_FLAG,STEP_COMPLETE_FLAG,COST_QTY_RECALC_FLAG,BATCH_SUM_FLAG,NAME_SEP_CHAR,DEF_COMPLETE_PCT_TYPE,PROJ_SHORT_NAME,ACCT_ID,ORIG_PROJ_ID,SOURCE_PROJ_ID,BASE_TYPE_ID,CLNDR_ID,SUM_BASE_PROJ_ID,TASK_CODE_BASE,TASK_CODE_STEP,PRIORITY_NUM,WBS_MAX_SUM_LEVEL,STRGY_PRIORITY_NUM,LAST_CHECKSUM,CRITICAL_DRTN_HR_CNT,DEF_COST_PER_QTY,LAST_RECALC_DATE,PLAN_START_DATE,PLAN_END_DATE,SCD_END_DATE,ADD_DATE,LAST_TASKSUM_DATE,FCST_START_DATE,DEF_DURATION_TYPE,TASK_CODE_PREFIX,GUID,DEF_QTY_TYPE,ADD_BY_NAME,WEB_LOCAL_ROOT_PATH,PROJ_URL,DEF_RATE_TYPE,ADD_ACT_REMAIN_FLAG,ACT_THIS_PER_LINK_FLAG,DEF_TASK_TYPE,ACT_PCT_LINK_FLAG,CRITICAL_PATH_TYPE,TASK_CODE_PREFIX_FLAG,DEF_ROLLUP_DATES_FLAG,USE_PROJECT_BASELINE_FLAG,REM_TARGET_LINK_FLAG,RESET_PLANNED_FLAG,ALLOW_NEG_ACT_FLAG,CHECKOUT_DATE,CHECKOUT_USER_ID,SUM_ASSIGN_LEVEL,LAST_FIN_DATES_ID,LAST_BASELINE_UPDATE_DATE,CR_EXTERNAL_KEY,APPLY_ACTUALS_DATE,LOCATION_ID,FINTMPL_ID,LAST_SCHEDULE_DATE,CONTROL_UPDATES_FLAG,HIST_INTERVAL,HIST_LEVEL,CREATE_DATE,CREATE_USER,UPDATE_DATE,UPDATE_USER,DELETE_SESSION_ID,DELETE_DATE
            )
            SELECT
              ?,FY_START_MONTH_NUM,RSRC_SELF_ADD_FLAG,ALLOW_COMPLETE_FLAG,RSRC_MULTI_ASSIGN_FLAG,CHECKOUT_FLAG,PROJECT_FLAG,STEP_COMPLETE_FLAG,COST_QTY_RECALC_FLAG,BATCH_SUM_FLAG,NAME_SEP_CHAR,DEF_COMPLETE_PCT_TYPE,?,ACCT_ID,NULL,NULL,BASE_TYPE_ID,CLNDR_ID,SUM_BASE_PROJ_ID,TASK_CODE_BASE,TASK_CODE_STEP,PRIORITY_NUM,WBS_MAX_SUM_LEVEL,STRGY_PRIORITY_NUM,LAST_CHECKSUM,CRITICAL_DRTN_HR_CNT,DEF_COST_PER_QTY,LAST_RECALC_DATE,?,PLAN_END_DATE,SCD_END_DATE,?,LAST_TASKSUM_DATE,?,DEF_DURATION_TYPE,TASK_CODE_PREFIX,GUID,DEF_QTY_TYPE,ADD_BY_NAME,WEB_LOCAL_ROOT_PATH,PROJ_URL,DEF_RATE_TYPE,ADD_ACT_REMAIN_FLAG,ACT_THIS_PER_LINK_FLAG,DEF_TASK_TYPE,ACT_PCT_LINK_FLAG,CRITICAL_PATH_TYPE,TASK_CODE_PREFIX_FLAG,DEF_ROLLUP_DATES_FLAG,USE_PROJECT_BASELINE_FLAG,REM_TARGET_LINK_FLAG,RESET_PLANNED_FLAG,ALLOW_NEG_ACT_FLAG,CHECKOUT_DATE,CHECKOUT_USER_ID,SUM_ASSIGN_LEVEL,LAST_FIN_DATES_ID,LAST_BASELINE_UPDATE_DATE,CR_EXTERNAL_KEY,APPLY_ACTUALS_DATE,LOCATION_ID,FINTMPL_ID,NULL,CONTROL_UPDATES_FLAG,HIST_INTERVAL,HIST_LEVEL,?,CREATE_USER,?,UPDATE_USER,DELETE_SESSION_ID,DELETE_DATE
            FROM PROJECT WHERE PROJ_ID=?
            """,
            (proj_id, args.new_short, args.new_start, args.new_start, args.new_start, args.new_start, now_str(), now_str(), args.template_proj_id),
        )

        cur.execute(
            """
            INSERT INTO PROJWBS (
              WBS_ID, PROJ_ID, OBS_ID, SEQ_NUM, EST_WT, PROJ_NODE_FLAG, SUM_DATA_FLAG, STATUS_CODE,
              WBS_SHORT_NAME, WBS_NAME, PHASE_ID, PARENT_WBS_ID, EV_USER_PCT, EV_ETC_USER_VALUE,
              ORIG_COST, INDEP_REMAIN_TOTAL_COST, ANN_DSCNT_RATE_PCT, DSCNT_PERIOD_TYPE,
              INDEP_REMAIN_WORK_QTY, ANTICIP_START_DATE, ANTICIP_END_DATE, EV_COMPUTE_TYPE, EV_ETC_COMPUTE_TYPE,
              GUID, TMPL_GUID, CREATE_DATE, CREATE_USER, UPDATE_DATE, UPDATE_USER, DELETE_SESSION_ID, DELETE_DATE
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                wbs_id, proj_id, None, seq, 0.0, 'Y', 'N', None,
                args.new_short, args.new_name, None, args.parent_wbs_id, None, None,
                None, None, None, None,
                None, args.new_start, None, None, None,
                None, None, now_str(), 'openclaw', now_str(), 'openclaw', None, None
            ),
        )

        set_next_id(cur, 'project_proj_id', proj_id + 1)
        set_next_id(cur, 'projwbs_wbs_id', wbs_id + 1)
        con.commit()
    except Exception:
        con.rollback()
        raise

    row = cur.execute(
        '''
        SELECT p.PROJ_ID, p.PROJ_SHORT_NAME, w.WBS_ID, w.PARENT_WBS_ID, w.WBS_NAME, p.PLAN_START_DATE
        FROM PROJECT p
        JOIN PROJWBS w ON w.PROJ_ID=p.PROJ_ID
        WHERE p.PROJ_ID=?
        ''',
        (proj_id,),
    ).fetchone()
    print(f"CREATED|PROJ_ID={row[0]}|SHORT={row[1]}|WBS_ID={row[2]}|PARENT={row[3]}|NAME={row[4]}|START={row[5]}")
    con.close()


if __name__ == '__main__':
    main()
