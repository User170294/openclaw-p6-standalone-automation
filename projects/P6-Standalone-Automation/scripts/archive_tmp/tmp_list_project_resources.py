import argparse
import sqlite3

ap = argparse.ArgumentParser()
ap.add_argument("--db", required=True)
ap.add_argument("--proj-id", type=int, required=True)
args = ap.parse_args()

con = sqlite3.connect(args.db)
con.row_factory = sqlite3.Row
cur = con.cursor()

# Summary
s = cur.execute(
    """
    SELECT COUNT(*) AS assignments,
           COUNT(DISTINCT RSRC_ID) AS distinct_rsrc,
           SUM(COALESCE(TARGET_QTY,0)) AS sum_target_qty,
           SUM(COALESCE(REMAIN_QTY,0)) AS sum_remain_qty,
           SUM(COALESCE(ACT_REG_QTY,0) + COALESCE(ACT_OT_QTY,0)) AS sum_actual_qty
    FROM TASKRSRC
    WHERE PROJ_ID = ?
    """,
    (args.proj_id,),
).fetchone()

print(f"PROJ_ID={args.proj_id}")
print(
    "SUMMARY|ASSIGNMENTS={}|DISTINCT_RSRC={}|TARGET_QTY={}|REMAIN_QTY={}|ACTUAL_QTY={}".format(
        s["assignments"] or 0,
        s["distinct_rsrc"] or 0,
        s["sum_target_qty"] or 0,
        s["sum_remain_qty"] or 0,
        s["sum_actual_qty"] or 0,
    )
)

# Resource list
rows = cur.execute(
    """
    SELECT tr.RSRC_ID,
           COALESCE(r.RSRC_SHORT_NAME,'') AS RSRC_SHORT_NAME,
           COALESCE(r.RSRC_NAME,'') AS RSRC_NAME,
           COALESCE(r.RSRC_TYPE,'') AS RSRC_TYPE,
           COUNT(*) AS ASSIGNMENTS,
           SUM(COALESCE(tr.TARGET_QTY,0)) AS TARGET_QTY,
           SUM(COALESCE(tr.REMAIN_QTY,0)) AS REMAIN_QTY,
           SUM(COALESCE(tr.ACT_REG_QTY,0) + COALESCE(tr.ACT_OT_QTY,0)) AS ACTUAL_QTY
    FROM TASKRSRC tr
    LEFT JOIN RSRC r ON r.RSRC_ID = tr.RSRC_ID
    WHERE tr.PROJ_ID = ?
    GROUP BY tr.RSRC_ID, r.RSRC_SHORT_NAME, r.RSRC_NAME, r.RSRC_TYPE
    ORDER BY ASSIGNMENTS DESC, tr.RSRC_ID
    """,
    (args.proj_id,),
).fetchall()

print(f"RESOURCES={len(rows)}")
for r in rows:
    print(
        f"RSRC|{r['RSRC_ID']}|{r['RSRC_SHORT_NAME']}|{r['RSRC_NAME']}|TYPE={r['RSRC_TYPE']}|"
        f"ASG={r['ASSIGNMENTS']}|TGT={r['TARGET_QTY'] or 0}|REM={r['REMAIN_QTY'] or 0}|ACT={r['ACTUAL_QTY'] or 0}"
    )

con.close()
