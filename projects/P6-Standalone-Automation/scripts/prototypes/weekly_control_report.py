"""Weekly Control Report OT-1844 - Programado (PV) vs Real (AC) vs Forecast (FC)"""
import glob,os
from pathlib import Path
from datetime import datetime,timedelta
from collections import defaultdict

TAB=chr(9); NL=chr(10); CR=chr(13)

base=os.path.expandvars("%USERPROFILE%") + "\\OneDrive - SIMTEXX SPA"
BASE_XER=Path(glob.glob(os.path.join(base,"PO 4519143302*","Planifica*","001*","*.xer"))[0])
UPD_XER=Path(glob.glob(os.path.join(base,"PO 4519143302*","Planifica*","004*","*W09*.xer"))[0])
CUTOFF=datetime(2026,2,22,23,59,59)
W08_MON=datetime(2026,2,16).date()

def week_label(m):
    d=(m-W08_MON).days
    if d<0:
        iy,iw,_=m.isocalendar()
        return "ISO{}-W{:02d}".format(iy,iw)
    return "W{:02d}".format(8+d//7)

def parse_table(path,tn):
    rows=[]; cur=None; flds=None
    with path.open("r",encoding="latin-1",errors="ignore") as fh:
        for raw in fh:
            ln=raw.rstrip(NL+CR)
            if not ln: continue
            parts=ln.split(TAB); tag=parts[0]
            if tag=="%T": cur=(parts[1] if len(parts)>1 else ""); flds=None
            elif tag=="%F" and cur==tn: flds=parts[1:]
            elif tag=="%R" and cur==tn and flds:
                vals=parts[1:]
                if len(vals)<len(flds): vals+=[""]*(len(flds)-len(vals))
                rows.append(dict(zip(flds,vals)))
    return rows

def sf(x):
    if x is None or x=="": return 0.0
    try: return float(x)
    except: return 0.0

def sdt(s):
    if not s or not s.strip(): return None
    s=s.strip()
    for fmt in ["%Y-%m-%d %H:%M","%Y-%m-%d %H:%M:%S","%Y-%m-%d"]:
        try: return datetime.strptime(s[:len(fmt)],fmt)
        except: pass
    return None

def spread_lv(sd,ed,qty,bkt):
    if not sd or not ed or ed<sd or qty<=0: return
    days=[]; d=sd
    while d<=ed:
        if d.weekday()<5: days.append(d)
        d+=timedelta(days=1)
    if not days: days=[sd]
    per=qty/len(days)
    for day in days:
        m=day-timedelta(days=day.weekday())
        bkt[m]+=per

def ps(v,t): return "{:6.2f}%".format(v/t*100) if t else "  0.00%"

# PV desde baseline
pv_w=defaultdict(float); bac=0.0
for r in parse_table(BASE_XER,"TASK"):
    hh=sf(r.get("target_work_qty"))
    ts=sdt(r.get("target_start_date"))
    te=sdt(r.get("target_end_date"))
    if hh<=0 or not ts or not te: continue
    bac+=hh
    spread_lv(ts.date(),te.date(),hh,pv_w)

# AC y FC desde control W09
ac_w=defaultdict(float); fc_w=defaultdict(float)
ac_tot=0.0; fc_tot=0.0
for r in parse_table(UPD_XER,"TASKRSRC"):
    act=sf(r.get("act_reg_qty"))
    rem=sf(r.get("remain_qty"))
    bac_i=sf(r.get("target_qty"))
    a_s=sdt(r.get("act_start_date"))
    a_e=sdt(r.get("act_end_date"))
    t_s=sdt(r.get("target_start_date"))
    t_e=sdt(r.get("target_end_date"))

    # AC hasta corte
    if a_s and a_s<=CUTOFF and act>0:
        ac_tot+=act
        e_ac=(a_e if (a_e and a_e<=CUTOFF) else CUTOFF).date()
        spread_lv(a_s.date(),e_ac,act,ac_w)

    # FC desde corte+1
    if a_s is None or a_s>CUTOFF:
        rc=rem if rem>0 else bac_i
    elif a_e is None or a_e>CUTOFF:
        rc=rem
    else:
        rc=0.0

    if rc>0:
        fc_tot+=rc
        fcs=(CUTOFF+timedelta(seconds=1)).date()
        if t_s and t_s.date()>fcs: fcs=t_s.date()
        fce=t_e.date() if t_e else fcs
        if fce<fcs: fce=fcs
        spread_lv(fcs,fce,rc,fc_w)

# Tabla
weeks=sorted(set(pv_w)|set(ac_w)|set(fc_w))
print("BAC={:.1f} HH | AC corte={:.1f} HH ({}) | FC={:.1f} HH | EAC={:.1f} HH".format(bac,ac_tot,ps(ac_tot,bac).strip(),fc_tot,ac_tot+fc_tot))
print("")
HDR="{:<8} | {:>8} {:>7} {:>7} | {:>8} {:>7} {:>7} | {:>8} {:>7} {:>7}".format("Semana","PV HH","PV%sem","PV%cum","AC HH","AC%sem","AC%cum","FC HH","FC%sem","FC%cum")
SEP="-"*len(HDR)
print(HDR)
print(SEP)
pvc=acc=fcc=0.0
for m in weeks:
    pvw=pv_w.get(m,0.0); acw=ac_w.get(m,0.0); fcw=fc_w.get(m,0.0)
    pvc+=pvw; acc+=acw; fcc+=fcw
    print("{:<8} | {:>8.1f} {:>7} {:>7} | {:>8.1f} {:>7} {:>7} | {:>8.1f} {:>7} {:>7}".format(
        week_label(m),pvw,ps(pvw,bac),ps(pvc,bac),acw,ps(acw,bac),ps(acc,bac),fcw,ps(fcw,bac),ps(fcc,bac)))
print(SEP)
print("{:<8} | {:>8.1f} {:>7} {:>7} | {:>8.1f} {:>7} {:>7} | {:>8.1f} {:>7} {:>7}".format(
    "TOTAL",bac,"100.00%","100.00%",ac_tot,ps(ac_tot,bac),ps(ac_tot,bac),fc_tot,ps(fc_tot,bac),ps(fc_tot,bac)))
