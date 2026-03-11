import csv
from datetime import datetime, timedelta
from collections import defaultdict
from pathlib import Path

BASE_XER = Path(r"C:\Users\josej\OneDrive - SIMTEXX SPA\PO 4519143302 Fabricación Bandejas Agua Lavado Celda_OT 1844 Celdas - Documentos\Planificación\001 Para Rev. Linea Base\SPC-2220-PS-PMS-011840_Fabricación Bandejas Agua Lavado Celdas OT 1844_Rev.B.xer")
UPD_XER = Path(r"C:\Users\josej\OneDrive - SIMTEXX SPA\PO 4519143302 Fabricación Bandejas Agua Lavado Celda_OT 1844 Celdas - Documentos\Planificación\004 Control W09\SPC-2220-PS-PMS-011840_Fabricación Bandejas Agua Lavado Celdas OT 1844_Rev.B_W09.xer")
CUTOFF = datetime(2026, 2, 22, 23, 59, 59)


def parse_xer_table(path: Path, table: str):
    rows = []
    current_table = None
    fields = None
    with path.open("r", encoding="latin-1", errors="ignore") as f:
        for raw in f:
            line = raw.rstrip("\n\r")
            if not line:
                continue
            if line.startswith("%T"):
                current_table = line.split("\t", 1)[1] if "\t" in line else ""
                fields = None
            elif line.startswith("%F") and current_table == table:
                fields = line.split("\t")[1:]
            elif line.startswith("%R") and current_table == table and fields:
                vals = line.split("\t")[1:]
                if len(vals) < len(fields):
                    vals += [""] * (len(fields) - len(vals))
                rows.append(dict(zip(fields, vals)))
    return rows


def dt(s):
    if not s:
        return None
    s = s.strip()
    for fmt in ("%Y-%m-%d %H:%M", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(s[:len(fmt.replace('%',''))], fmt)
        except Exception:
            pass
    # fallback robust for standard
    try:
        return datetime.strptime(s[:16], "%Y-%m-%d %H:%M")
    except Exception:
        return None


def f(x):
    try:
        return float(x) if x not in (None, "") else 0.0
    except Exception:
        return 0.0


def spread_weekdays(start_d, end_d, qty, bucket):
    if end_d < start_d:
        return
    days = []
    d = start_d
    while d <= end_d:
        if d.weekday() < 5:
            days.append(d)
        d += timedelta(days=1)
    if not days:
        days = [start_d]
    per = qty / len(days) if days else 0.0
    for day in days:
        monday = day - timedelta(days=day.weekday())
        bucket[monday] += per


# PV from baseline TASK
base_task = parse_xer_table(BASE_XER, "TASK")
pv_week = defaultdict(float)
bac = 0.0
for r in base_task:
    ts = dt(r.get("target_start_date", ""))
    te = dt(r.get("target_end_date", ""))
    hh = f(r.get("target_work_qty", "0"))
    if not ts or not te or hh <= 0:
        continue
    bac += hh
    spread_weekdays(ts.date(), te.date(), hh, pv_week)

# EV/ETC from updated TASKRSRC
upd_rsrc = parse_xer_table(UPD_XER, "TASKRSRC")
ev_week = defaultdict(float)
etc_week = defaultdict(float)
ev_total = 0.0
etc_total = 0.0
for r in upd_rsrc:
    bac_i = f(r.get("target_qty", "0"))
    act_i = f(r.get("act_reg_qty", "0"))
    rem_i = f(r.get("remain_qty", "0"))

    a_s = dt(r.get("act_start_date", ""))
    a_e = dt(r.get("act_end_date", ""))
    t_s = dt(r.get("target_start_date", ""))
    t_e = dt(r.get("target_end_date", ""))

    # EV at cutoff
    if a_s and a_s <= CUTOFF and act_i > 0:
        ev_total += act_i
        s = a_s.date()
        e = (a_e if (a_e and a_e <= CUTOFF) else CUTOFF).date()
        spread_weekdays(s, e, act_i, ev_week)

    # ETC at cutoff snapshot
    if (not a_s) or a_s > CUTOFF:
        rem_cut = rem_i if rem_i > 0 else bac_i
    elif a_e and a_e <= CUTOFF:
        rem_cut = 0.0
    else:
        rem_cut = rem_i

    if rem_cut <= 0:
        continue

    etc_total += rem_cut
    s2 = (CUTOFF + timedelta(seconds=1)).date()
    if t_s and t_s.date() > s2:
        s2 = t_s.date()
    e2 = t_e.date() if t_e else s2
    spread_weekdays(s2, e2, rem_cut, etc_week)

weeks = sorted(set(pv_week.keys()) | set(ev_week.keys()) | set(etc_week.keys()))

print(f"BAC_HH={bac:.3f}|EV_CUTOFF={ev_total:.3f}|ETC_CUTOFF={etc_total:.3f}|EAC={ev_total+etc_total:.3f}")
print("WEEK|PV_HH_WEEK|PV_%_WEEK|PV_%_CUM|EV_HH_WEEK|EV_%_WEEK|EV_%_CUM|ETC_HH_WEEK|ETC_%_WEEK|ETC_%_CUM|EAC_HH_CUM|EAC_%_CUM")

pv_c = ev_c = etc_c = 0.0
for m in weeks:
    pvw = pv_week.get(m, 0.0)
    evw = ev_week.get(m, 0.0)
    etcw = etc_week.get(m, 0.0)

    pv_c += pvw
    ev_c += evw
    etc_c += etcw
    eac_c = ev_total + etc_c

    y, w, _ = m.isocalendar()
    print(
        f"ISO{y}-W{w:02d}|{pvw:.3f}|{(pvw/bac*100 if bac else 0):.2f}|{(pv_c/bac*100 if bac else 0):.2f}|"
        f"{evw:.3f}|{(evw/bac*100 if bac else 0):.2f}|{(ev_c/bac*100 if bac else 0):.2f}|"
        f"{etcw:.3f}|{(etcw/bac*100 if bac else 0):.2f}|{(etc_c/bac*100 if bac else 0):.2f}|"
        f"{eac_c:.3f}|{(eac_c/bac*100 if bac else 0):.2f}"
    )
