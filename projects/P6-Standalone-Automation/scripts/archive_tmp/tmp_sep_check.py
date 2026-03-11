from pathlib import Path
BASE_XER = Path(r"C:\Users\josej\OneDrive - SIMTEXX SPA\PO 4519143302 Fabricación Bandejas Agua Lavado Celda_OT 1844 Celdas - Documentos\Planificación\001 Para Rev. Linea Base\SPC-2220-PS-PMS-011840_Fabricación Bandejas Agua Lavado Celdas OT 1844_Rev.B.xer")
with BASE_XER.open("rb") as f:
    raw = f.read(2000)
# print hex of first 500 bytes
for i in range(0, min(500, len(raw)), 16):
    chunk = raw[i:i+16]
    hex_part = ' '.join(f'{b:02x}' for b in chunk)
    chr_part = ''.join(chr(b) if 32<=b<127 else '.' for b in chunk)
    print(f"{i:04x}  {hex_part:<48}  {chr_part}")
