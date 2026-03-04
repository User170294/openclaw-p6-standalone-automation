import os
import pythoncom
import win32com.client

TARGET_DOC = "Drawing3.dwg"
TARGET_BLOCK = "BRAZO2"

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

# Backup simple en misma carpeta si existe ruta
try:
    full = str(doc.FullName)
except Exception:
    full = ""

if full and os.path.exists(full):
    backup = os.path.join(os.path.dirname(full), os.path.splitext(os.path.basename(full))[0] + "_before_pilot.dwg")
    try:
        doc.SaveAs(backup)
        print(f"Backup creado: {backup}")
    except Exception as e:
        print(f"No se pudo crear backup automático: {e}")

ms = doc.ModelSpace
found = None
for i in range(ms.Count):
    ent = ms.Item(i)
    if getattr(ent, "ObjectName", "") != "AcDbBlockReference":
        continue
    name = getattr(ent, "EffectiveName", None) or getattr(ent, "Name", "")
    if str(name).strip().upper() == TARGET_BLOCK.upper():
        found = ent
        break

if found is None:
    raise RuntimeError(f"No encontré bloque '{TARGET_BLOCK}' en {TARGET_DOC}")

handle = getattr(found, "Handle", "")
print(f"Bloque encontrado. Handle={handle}. Ejecutando explode piloto...")

created = found.Explode()
created_count = 0
try:
    created_count = len(created)
except Exception:
    # COM variant may not support len directly
    try:
        created_count = created.Count
    except Exception:
        created_count = -1

print(f"Explode ejecutado. Entidades creadas aprox: {created_count}")

# Mantener solo resultado explotado para el piloto
found.Delete()
print("Bloque original eliminado (solo en Drawing3 de prueba).")

try:
    doc.Save()
    print("Drawing3 guardado.")
except Exception as e:
    print(f"No se pudo guardar automáticamente: {e}")
