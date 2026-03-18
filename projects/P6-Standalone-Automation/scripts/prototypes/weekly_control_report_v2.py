"""Weekly Control Report OT-1844 — v2"""
import sys
from pathlib import Path
from datetime import datetime, timedelta
from collections import defaultdict

BASE_XER = Path(r"C:\Users\josej\OneDrive - SIMTEXX SPA\PO 4519143302 Fabricación Bandejas Agua Lavado Celda_OT 1844 Celdas - Documentos\Planificación\001 Para Rev. Linea Base\SPC-2220-PS-PMS-011840_Fabricación Bandejas Agua Lavado Celdas OT 1844_Rev.B.xer")
UPD_XER  = Path(r"C:\Users\josej\OneDrive - SIMTEXX SPA\PO 4519143302 Fabricación Bandejas Agua Lavado Celda_OT 1844 Celdas - Documentos\Planificación\004 Control W09\SPC-2220-PS-PMS-011840_Fabricación Bandejas Agua Lavado Celdas OT 1844_Rev.B_W09.xer")
CUTOFF   = datetime(2026, 2, 22, 23, 59, 59)
W08_MON  = datetime(2026, 2, 16).date()

# ── helpers ────────────────────────────────────────────────────────────────────
def week_label(mon):
    delta = (mon - W08_MON).days
    if delta < 0:
        iy,iw,_ = mon.isocalendar()
        return f"ISO{iy}-W{iw:02d}"
    return f"W{8 + delta//7:02d}"

def parse_table(path, table_name):
    rows=[]; cur=None; flds=None
    with path.open("r", encoding="latin-1", errors="ignore") as fh:
        for raw in fh:
            ln = raw.rstrip("\n\r")
            if not ln: continue
            parts = ln.split("\t")
            tag = parts[0]
            if tag == "%T":
                cur = parts[1] if len(parts)>1 else ""; flds=None
            elif tag == "%F" and cur == table_name:
                flds = parts[1:]
            elif tag == "%R" and cur == table_name and flds:
                vals = parts[1:]
                if len(vals)<len(flds): vals += [""]*(len(flds)-len(vals))
                rows.append(dict(zip(flds, vals)))
    return rows

def safe_float(x):
    if x is None or x == "": return 0.0
    try: return float(x)
    except: return 0.0

def safe_dt(s):
    if not s or not s.strip(): return None
    s = s.strip()
    for fmt in ["%Y-%m-%d %H:%M","%Y-%m-%d %H:%M:%S","%Y-%m-%d"]:
        try: return datetime.strptime(s[:len(fmt)],fmt)
        except: pass
    return None

def spread_lv(start_d, end_d, qty, bucket):
    if not start_d or not end_d or end_d < start_d or qty <= 0: return
    days=[]; d=start_d
    while d<=end_d:
        if d.weekday()<5: days.append(d)
        d+=timedelta(days=1)
    if not days: days=[start_d]
    per = qty/len(days)
    for day in days:
        mon = day - timedelta(days=day.weekday())
        bucket[mon] += per

def pct_str(v, total):
    return f"{v/total*100:6.2f}%" if total else "  0.00%"

# ── PV desde baseline ──────────────────────────────────────────────────────────
pv_w = defaultdict(float)
bac  = 0.0

task_list = parse_table(BASE_XER, "TASK")
sys.stderr.write(f"[debug] TASK filas={len(task_list)}\n")
for row in task_list:
    hh = safe_float(row.get("target_work_qty"))
    ts = safe_dt(row.get("target_start_date"))
    te = safe_dt(row.get("target_end_date"))
    sys.stderr.write(f"  hh={hh!r} ts={row.get('target_start_date')!r} te={row.get('target_end_date')!r}\n")
    if hh <= 0 or not ts or not te: continue
    bac += hh
    spread_lv(ts.date(), te.date(), hh, pv_w)
    if bac >= 8100: break   # stop debug after first hit for brevity

sys.stderr.write(f"[debug] BAC={bac}\n")
