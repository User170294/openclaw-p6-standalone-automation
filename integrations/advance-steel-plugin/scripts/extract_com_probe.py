import csv
import os
import sys
import time
from collections import Counter

import pythoncom
import win32com.client

DWG_PATH = r"C:\Users\josej\OneDrive - SIMTEXX SPA\PO 4519143302 Fabricación Bandejas Agua Lavado Celda_OT 1844 Celdas - Documentos\Ingeniería Fabricación\002 Modelo Coordinación\MODELO 16_02.dwg"
OUT_CSV = r"C:\Users\josej\.openclaw\workspace\integrations\advance-steel-plugin\out\com_probe_entities.csv"


def safe_get(obj, name, default=None):
    try:
        return getattr(obj, name)
    except Exception:
        return default


def main():
    pythoncom.CoInitialize()

    # Prefer active session (Advance Steel/AutoCAD already open), fallback to launching AutoCAD.
    app = None
    try:
        app = win32com.client.GetActiveObject("AutoCAD.Application")
        print("Connected to active AutoCAD session")
    except Exception:
        app = win32com.client.Dispatch("AutoCAD.Application")
        app.Visible = True
        print("Started new AutoCAD session")

    docs = app.Documents
    doc = None

    # Reuse already-open target drawing when possible.
    target_norm = os.path.normcase(os.path.abspath(DWG_PATH))
    for i in range(docs.Count):
        d = docs.Item(i)
        try:
            if os.path.normcase(os.path.abspath(d.FullName)) == target_norm:
                doc = d
                break
        except Exception:
            pass

    if doc is None:
        print(f"Opening DWG: {DWG_PATH}")
        last_err = None
        for attempt in range(1, 11):
            try:
                pythoncom.PumpWaitingMessages()
                doc = docs.Open(DWG_PATH)
                break
            except Exception as e:
                last_err = e
                print(f"Open attempt {attempt}/10 failed: {e}")
                time.sleep(1.5)
        if doc is None:
            raise last_err

    # Bring active and let UI/COM settle
    for _ in range(5):
        try:
            doc.Activate()
            break
        except Exception:
            time.sleep(0.5)
    time.sleep(1.5)

    ms = doc.ModelSpace
    print(f"ModelSpace entities: {ms.Count}")

    os.makedirs(os.path.dirname(OUT_CSV), exist_ok=True)
    rows = []
    by_type = Counter()

    max_scan = min(ms.Count, 50000)
    for i in range(max_scan):
        try:
            ent = ms.Item(i)
        except Exception:
            continue

        obj_name = safe_get(ent, "ObjectName", "")
        layer = safe_get(ent, "Layer", "")
        handle = safe_get(ent, "Handle", "")
        length = safe_get(ent, "Length", None)

        # Some entities expose area/volume
        area = safe_get(ent, "Area", None)
        volume = safe_get(ent, "Volume", None)

        by_type[obj_name] += 1
        rows.append({
            "index": i,
            "handle": handle,
            "object_name": obj_name,
            "layer": layer,
            "length": length,
            "area": area,
            "volume": volume,
        })

    with open(OUT_CSV, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["index", "handle", "object_name", "layer", "length", "area", "volume"])
        w.writeheader()
        w.writerows(rows)

    print(f"Wrote probe CSV: {OUT_CSV}")
    print("Top entity types:")
    for name, cnt in by_type.most_common(20):
        print(f"  {name}: {cnt}")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print("ERROR:", e)
        sys.exit(1)
