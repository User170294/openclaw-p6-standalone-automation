from pathlib import Path
BASE_XER = Path(r"C:\Users\josej\OneDrive - SIMTEXX SPA\PO 4519143302 Fabricación Bandejas Agua Lavado Celda_OT 1844 Celdas - Documentos\Planificación\001 Para Rev. Linea Base\SPC-2220-PS-PMS-011840_Fabricación Bandejas Agua Lavado Celdas OT 1844_Rev.B.xer")

def parse_table(path, table):
    rows = []; cur_tbl = None; fields = None
    with path.open("r", encoding="latin-1", errors="ignore") as fh:
        for raw in fh:
            line = raw.rstrip("\n\r")
            if not line: continue
            if line.startswith("%T"):
                cur_tbl = line.split("\t", 1)[1] if "\t" in line else ""
                fields = None
            elif line.startswith("%F") and cur_tbl == table:
                fields = line.split("\t")[1:]
            elif line.startswith("%R") and cur_tbl == table and fields:
                vals = line.split("\t")[1:]
                if len(vals) < len(fields):
                    vals += [""] * (len(fields) - len(vals))
                rows.append(dict(zip(fields, vals)))
    return rows

tasks = parse_table(BASE_XER, "TASK")
print(f"TASKS={len(tasks)}")
hh_vals = [float(r.get("target_work_qty","0") or "0") for r in tasks]
print(f"total_hh={sum(hh_vals):.1f}")
print(f"non_zero_hh={sum(1 for v in hh_vals if v>0)}")
# date sample
for r in tasks[:5]:
    print(f"  {r.get('task_code')} | tgt_s={r.get('target_start_date')} | tgt_e={r.get('target_end_date')} | hh={r.get('target_work_qty')}")
