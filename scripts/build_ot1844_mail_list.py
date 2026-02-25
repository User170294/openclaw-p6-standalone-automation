import csv
from pathlib import Path

p = Path(r"projects/OT-1844/emails/processed/ot1844_000_correos_index.csv")
rows = list(csv.DictReader(p.open(encoding="utf-8-sig")))


def is_me(t: str) -> bool:
    t = (t or "").lower()
    return (
        "jose jorquera calderon" in t
        or "j.jorquera@simtexx.cl" in t
        or "jose.jorquera" in t
    )


for r in rows:
    s = r.get("de", "")
    to = r.get("para", "")
    cc = r.get("cc", "")
    if is_me(s):
        r["tipo2"] = "Enviado"
    elif is_me(to) or is_me(cc):
        r["tipo2"] = "Recibido"
    else:
        r["tipo2"] = "Indeterminado"

rows.sort(key=lambda r: r.get("fecha", ""), reverse=True)

out = Path(r"projects/OT-1844/emails/processed/ot1844_000_correos_listado.md")
lines: list[str] = []
lines.append("# Listado indexado — 000 Correos (OT-1844)")
lines.append("")
lines.append(f"- Total: {len(rows)}")
for k in ["Enviado", "Recibido", "Indeterminado"]:
    lines.append(f"- {k}: {sum(1 for r in rows if r['tipo2'] == k)}")
lines.append("")

for sec in ["Enviado", "Recibido", "Indeterminado"]:
    lines.append(f"## {sec}s")
    lines.append("")
    lines.append("| fecha | asunto | de | para | adjuntos | archivo |")
    lines.append("|---|---|---|---|---:|---|")
    for r in [x for x in rows if x["tipo2"] == sec]:
        fecha = (r.get("fecha", "") or "")[:16]
        asunto = (r.get("asunto", "") or "").replace("|", "/").strip()
        de = (r.get("de", "") or "").replace("|", "/").strip()
        para = (r.get("para", "") or "").replace("|", "/").strip()
        archivo = (r.get("archivo", "") or "").replace("|", "/").strip()
        adj_n = r.get("adjuntos_n", "0")
        lines.append(f"| {fecha} | {asunto} | {de} | {para} | {adj_n} | {archivo} |")
    lines.append("")

out.write_text("\n".join(lines), encoding="utf-8")
print(out)
