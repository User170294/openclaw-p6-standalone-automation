import csv
from collections import Counter, defaultdict
import pythoncom
import win32com.client

DWG_PATH = r"C:\Users\josej\OneDrive - SIMTEXX SPA\PO 4519143302 Fabricación Bandejas Agua Lavado Celda_OT 1844 Celdas - Documentos\Ingeniería Fabricación\002 Modelo Coordinación\MODELO 16_02.dwg"
OUT_SUMMARY = r"C:\Users\josej\.openclaw\workspace\integrations\advance-steel-plugin\out\block_summary.csv"
OUT_ATTRS = r"C:\Users\josej\.openclaw\workspace\integrations\advance-steel-plugin\out\block_attrs.csv"

pythoncom.CoInitialize()
app = win32com.client.GetActiveObject("AutoCAD.Application")
docs = app.Documents

doc = None
for i in range(docs.Count):
    d = docs.Item(i)
    if str(d.FullName).lower() == DWG_PATH.lower():
        doc = d
        break
if doc is None:
    doc = docs.Open(DWG_PATH)

doc.Activate()
ms = doc.ModelSpace

by_block = Counter()
rows = []
attr_rows = []
for i in range(ms.Count):
    ent = ms.Item(i)
    if getattr(ent, "ObjectName", "") != "AcDbBlockReference":
        continue

    name = getattr(ent, "EffectiveName", None) or getattr(ent, "Name", "")
    by_block[name] += 1
    rows.append({"block_name": name, "layer": getattr(ent, "Layer", ""), "handle": getattr(ent, "Handle", "")})

    has_attrs = False
    try:
        has_attrs = bool(ent.HasAttributes)
    except Exception:
        pass

    if has_attrs:
        try:
            attrs = ent.GetAttributes()
            for a in attrs:
                attr_rows.append({
                    "block_name": name,
                    "handle": getattr(ent, "Handle", ""),
                    "tag": getattr(a, "TagString", ""),
                    "value": getattr(a, "TextString", ""),
                })
        except Exception:
            pass

with open(OUT_SUMMARY, "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["block_name", "count"])
    for n, c in by_block.most_common():
        w.writerow([n, c])

with open(OUT_ATTRS, "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=["block_name", "handle", "tag", "value"])
    w.writeheader()
    w.writerows(attr_rows)

print("Top blocks:")
for n, c in by_block.most_common(20):
    print(f"{n}: {c}")
print(f"Attributes rows: {len(attr_rows)}")
print(OUT_SUMMARY)
print(OUT_ATTRS)
