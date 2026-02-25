import csv
from pathlib import Path
from datetime import datetime
import json

import extract_msg

SRC = Path(r"C:\Users\josej\OneDrive - SIMTEXX SPA\PO 4519143302 Fabricación Bandejas Agua Lavado Celda_OT 1844 Celdas - Documentos\Planificación\000 Correos")
OUT_CSV = Path(r"C:\Users\josej\.openclaw\workspace\projects\OT-1844\emails\processed\ot1844_000_correos_index.csv")
OUT_JSON = Path(r"C:\Users\josej\.openclaw\workspace\projects\OT-1844\emails\processed\ot1844_000_correos_index.json")

MY_MAILS = {"j.jorquera@simtexx.cl", "jose.jorquera@simtexx.cl", "j.jorquera@outlook.es"}


def norm(s: str | None) -> str:
    return (s or "").replace("\r", " ").replace("\n", " ").strip()


def infer_tipo(sender: str, to: str, cc: str) -> str:
    text = f"{sender} {to} {cc}".lower()
    sender_l = sender.lower()
    if any(m in sender_l for m in MY_MAILS):
        return "Enviado"
    if any(m in text for m in MY_MAILS):
        return "Recibido"
    return "Indeterminado"


rows = []
for p in sorted(SRC.rglob("*.msg")):
    try:
        m = extract_msg.Message(str(p))
        subj = norm(m.subject)
        sender = norm(m.sender)
        to = norm(m.to)
        cc = norm(m.cc)
        date_raw = norm(str(m.date))
        body = norm(m.body)
        preview = body[:220]
        atts = []
        for a in (m.attachments or []):
            name = getattr(a, "longFilename", None) or getattr(a, "shortFilename", None) or "adjunto"
            atts.append(norm(str(name)))
        tipo = infer_tipo(sender, to, cc)
        rows.append({
            "fecha": date_raw,
            "tipo": tipo,
            "asunto": subj,
            "de": sender,
            "para": to,
            "cc": cc,
            "adjuntos": " | ".join(atts[:8]),
            "adjuntos_n": len(atts),
            "preview": preview,
            "archivo": p.name,
            "ruta": str(p),
        })
    except Exception as e:
        rows.append({
            "fecha": "",
            "tipo": "Error",
            "asunto": "",
            "de": "",
            "para": "",
            "cc": "",
            "adjuntos": "",
            "adjuntos_n": 0,
            "preview": f"ERROR: {e}",
            "archivo": p.name,
            "ruta": str(p),
        })

OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
with OUT_CSV.open("w", newline="", encoding="utf-8-sig") as f:
    w = csv.DictWriter(f, fieldnames=["fecha","tipo","asunto","de","para","cc","adjuntos_n","adjuntos","preview","archivo","ruta"])
    w.writeheader()
    w.writerows(rows)

OUT_JSON.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")

print(f"INDEXED:{len(rows)}")
print(f"CSV:{OUT_CSV}")
print(f"JSON:{OUT_JSON}")
