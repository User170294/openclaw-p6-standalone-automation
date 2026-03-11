from pathlib import Path
BASE_XER = Path(r"C:\Users\josej\OneDrive - SIMTEXX SPA\PO 4519143302 Fabricación Bandejas Agua Lavado Celda_OT 1844 Celdas - Documentos\Planificación\001 Para Rev. Linea Base\SPC-2220-PS-PMS-011840_Fabricación Bandejas Agua Lavado Celdas OT 1844_Rev.B.xer")
count=0
with BASE_XER.open("r", encoding="latin-1", errors="ignore") as f:
    for line in f:
        line=line.rstrip("\n\r")
        if line.startswith("%F") and "TASK" in line:
            print(f"F_LINE: {repr(line[:200])}")
        if line.startswith("%R") and count<3:
            print(f"R_LINE: {repr(line[:300])}")
            count+=1
