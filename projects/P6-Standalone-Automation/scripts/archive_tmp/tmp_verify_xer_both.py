from pathlib import Path
from datetime import datetime

BASE_XER = Path(r"C:\Users\josej\OneDrive - SIMTEXX SPA\PO 4519143302 Fabricación Bandejas Agua Lavado Celda_OT 1844 Celdas - Documentos\Planificación\001 Para Rev. Linea Base\SPC-2220-PS-PMS-011840_Fabricación Bandejas Agua Lavado Celdas OT 1844_Rev.B.xer")
UPD_XER = Path(r"C:\Users\josej\OneDrive - SIMTEXX SPA\PO 4519143302 Fabricación Bandejas Agua Lavado Celda_OT 1844 Celdas - Documentos\Planificación\004 Control W09\SPC-2220-PS-PMS-011840_Fabricación Bandejas Agua Lavado Celdas OT 1844_Rev.B_W09.xer")

def parse_xer_table(path, table):
    rows = []; current_table = None; fields = None
    with path.open("r", encoding="latin-1", errors="ignore") as f:
        for raw in f:
            line = raw.rstrip("\n\r")
            if not line: continue
            if line.startswith("%T"):
                current_table = line.split("\t",1)[1] if "\t" in line else ""
                fields = None
            elif line.startswith("%F") and current_table == table:
                fields = line.split("\t")[1:]
            elif line.startswith("%R") and current_table == table and fields:
                vals = line.split("\t")[1:]
                if len(vals) < len(fields): vals += [""]*(len(fields)-len(vals))
                rows.append(dict(zip(fields, vals)))
    return rows

def flt(x):
    try: return float(x) if x not in (None,"") else 0.0
    except: return 0.0

def dt(s):
    if not s or not s.strip(): return None
    for fmt in ["%Y-%m-%d %H:%M", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"]:
        try: return datetime.strptime(s.strip()[:len(fmt)], fmt)
        except: pass
    return None

# === BASELINE XER ===
print("=== BASELINE (Rev.B) ===")
b_project = parse_xer_table(BASE_XER, "PROJECT")
b_task = parse_xer_table(BASE_XER, "TASK")
b_rsrc = parse_xer_table(BASE_XER, "TASKRSRC")
b_tables = []
with BASE_XER.open("r", encoding="latin-1", errors="ignore") as f:
    for l in f:
        if l.startswith("%T"):
            t = l.strip().split("\t",1)
            if len(t)>1: b_tables.append(t[1])

print(f"Tables in XER: {b_tables}")
for p in b_project:
    print(f"PROJECT: short={p.get('proj_short_name','')} | plan_start={p.get('plan_start_date','')} | plan_end={p.get('plan_end_date','')} | last_sched={p.get('last_schedule_date','')}")
print(f"TASK count={len(b_task)}")
print(f"TASKRSRC count={len(b_rsrc)}")
bac_task = sum(flt(r.get("target_work_qty","0")) for r in b_task)
bac_rsrc = sum(flt(r.get("target_qty","0")) for r in b_rsrc)
print(f"BAC from TASK.target_work_qty={bac_task:.3f}")
print(f"BAC from TASKRSRC.target_qty={bac_rsrc:.3f}")
# Sample first 3 tasks
print("TASK sample (first 3):")
for r in b_task[:3]:
    print(f"  {r.get('task_code','')} | {r.get('task_name','')} | tgt_start={r.get('target_start_date','')} | tgt_end={r.get('target_end_date','')} | hh={r.get('target_work_qty','')}")
# date ranges
starts = [dt(r.get("target_start_date","")) for r in b_task if dt(r.get("target_start_date",""))]
ends = [dt(r.get("target_end_date","")) for r in b_task if dt(r.get("target_end_date",""))]
if starts and ends:
    print(f"TASK date range: {min(starts)} → {max(ends)}")

# === UPDATED XER ===
print("\n=== UPDATED W09 (Rev.B_W09) ===")
u_project = parse_xer_table(UPD_XER, "PROJECT")
u_task = parse_xer_table(UPD_XER, "TASK")
u_rsrc = parse_xer_table(UPD_XER, "TASKRSRC")
u_tables = []
with UPD_XER.open("r", encoding="latin-1", errors="ignore") as f:
    for l in f:
        if l.startswith("%T"):
            t2 = l.strip().split("\t",1)
            if len(t2)>1: u_tables.append(t2[1])

print(f"Tables in XER: {u_tables}")
for p in u_project:
    print(f"PROJECT: short={p.get('proj_short_name','')} | plan_start={p.get('plan_start_date','')} | plan_end={p.get('plan_end_date','')} | last_sched={p.get('last_schedule_date','')} | data_date={p.get('last_recalc_date','')}")
print(f"TASK count={len(u_task)}")
print(f"TASKRSRC count={len(u_rsrc)}")
upd_bac_task = sum(flt(r.get("target_work_qty","0")) for r in u_task)
upd_bac_rsrc = sum(flt(r.get("target_qty","0")) for r in u_rsrc)
upd_act = sum(flt(r.get("act_reg_qty","0")) for r in u_rsrc)
upd_rem = sum(flt(r.get("remain_qty","0")) for r in u_rsrc)
print(f"BAC from TASK.target_work_qty={upd_bac_task:.3f}")
print(f"BAC from TASKRSRC.target_qty={upd_bac_rsrc:.3f}")
print(f"ACT_REG_QTY total={upd_act:.3f}")
print(f"REMAIN_QTY total={upd_rem:.3f}")
print(f"EAC snapshot (ACT+REMAIN)={upd_act+upd_rem:.3f}")
# tasks with actuals
act_tasks = [r for r in u_rsrc if flt(r.get("act_reg_qty","0")) > 0]
print(f"TASKRSRC rows with ACT_REG_QTY>0: {len(act_tasks)}")
# data date / last_recalc
starts2 = [dt(r.get("target_start_date","")) for r in u_task if dt(r.get("target_start_date",""))]
ends2 = [dt(r.get("target_end_date","")) for r in u_task if dt(r.get("target_end_date",""))]
if starts2 and ends2:
    print(f"TASK date range: {min(starts2)} → {max(ends2)}")
# Sample tasks with actuals
print("TASKRSRC sample with actuals (first 5):")
for r in act_tasks[:5]:
    print(f"  TASKRSRC | tgt_start={r.get('target_start_date','')} | tgt_end={r.get('target_end_date','')} | act_start={r.get('act_start_date','')} | act_end={r.get('act_end_date','')} | act={r.get('act_reg_qty','')} | rem={r.get('remain_qty','')}")
