from pathlib import Path

BASE_XER = Path(r"C:\Users\josej\OneDrive - SIMTEXX SPA\PO 4519143302 Fabricación Bandejas Agua Lavado Celda_OT 1844 Celdas - Documentos\Planificación\001 Para Rev. Linea Base\SPC-2220-PS-PMS-011840_Fabricación Bandejas Agua Lavado Celdas OT 1844_Rev.B.xer")
UPD_XER  = Path(r"C:\Users\josej\OneDrive - SIMTEXX SPA\PO 4519143302 Fabricación Bandejas Agua Lavado Celda_OT 1844 Celdas - Documentos\Planificación\004 Control W09\SPC-2220-PS-PMS-011840_Fabricación Bandejas Agua Lavado Celdas OT 1844_Rev.B_W09.xer")

def print_fields(path, tables_to_check):
    cur = None; fields = None
    with path.open("r", encoding="latin-1", errors="ignore") as f:
        for raw in f:
            line = raw.rstrip("\n\r")
            if not line: continue
            if line.startswith("%T"):
                cur = line.split("\t",1)[1] if "\t" in line else ""
                fields = None
            elif line.startswith("%F") and cur in tables_to_check:
                fields = line.split("\t")[1:]
                print(f"{path.name} | {cur} fields: {fields}")
            elif line.startswith("%R") and cur in tables_to_check and fields:
                vals = line.split("\t")[1:]
                row = dict(zip(fields, vals))
                # print first data row
                print(f"  SAMPLE: {dict(list(row.items())[:10])}")
                break

print("=== BASELINE ===")
print_fields(BASE_XER, ["TASK","TASKRSRC"])
print("=== UPDATED ===")
print_fields(UPD_XER, ["TASK","TASKRSRC"])
