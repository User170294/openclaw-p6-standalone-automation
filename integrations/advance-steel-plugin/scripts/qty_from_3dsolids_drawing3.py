import csv
import math
import pythoncom
import win32com.client

TARGET_DOC = "Drawing3.dwg"
OUT_CSV = r"C:\Users\josej\.openclaw\workspace\integrations\advance-steel-plugin\out\drawing3_qty_solids.csv"
DENSITY_KG_M3 = 7850.0  # acero carbono aproximado


def mm3_to_m3(v_mm3: float) -> float:
    return v_mm3 / 1_000_000_000.0


def mm_to_m(v_mm: float) -> float:
    return v_mm / 1000.0


pythoncom.CoInitialize()
app = win32com.client.GetActiveObject("AutoCAD.Application")
docs = app.Documents

doc = None
for i in range(docs.Count):
    d = docs.Item(i)
    if str(d.Name).lower() == TARGET_DOC.lower():
        doc = d
        break
if doc is None:
    raise RuntimeError(f"No encontré {TARGET_DOC} abierto")

doc.Activate()
ms = doc.ModelSpace

rows = []
for i in range(ms.Count):
    ent = ms.Item(i)
    if getattr(ent, "ObjectName", "") != "AcDb3dSolid":
        continue

    handle = getattr(ent, "Handle", "")

    # Bounding box
    min_pt, max_pt = ent.GetBoundingBox()
    dx = float(max_pt[0] - min_pt[0])
    dy = float(max_pt[1] - min_pt[1])
    dz = float(max_pt[2] - min_pt[2])
    length_mm = max(dx, dy, dz)

    # Volume property (drawing units^3, typically mm^3)
    volume_mm3 = float(ent.Volume)
    volume_m3 = mm3_to_m3(volume_mm3)
    weight_kg = volume_m3 * DENSITY_KG_M3

    rows.append({
        "handle": handle,
        "profile": "SOLID_GENERIC",
        "length_m": round(mm_to_m(length_mm), 4),
        "volume_m3": round(volume_m3, 6),
        "weight_kg": round(weight_kg, 3),
    })

with open(OUT_CSV, "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=["handle", "profile", "length_m", "volume_m3", "weight_kg"])
    w.writeheader()
    w.writerows(rows)

print(f"3D solids quantified: {len(rows)}")
print(f"CSV: {OUT_CSV}")
print(f"Total weight kg: {round(sum(r['weight_kg'] for r in rows),3)}")
