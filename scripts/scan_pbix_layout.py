import json, zipfile, re
from pathlib import Path

base = Path(r"C:\Users\josej\OneDrive\002 SIMTEXX\000_Control de Porcesos\004_Informe M.Munizaga")
pbix_files = sorted(base.glob("*.pbix"))

report = []
for p in pbix_files:
    item = {"file": p.name, "pages": 0, "visual_containers": 0, "gastos_hits": [], "layout_parse": ""}
    try:
        with zipfile.ZipFile(p, "r") as z:
            raw = z.read("Report/Layout")
        # Layout suele venir UTF-16-LE en PBIX antiguos
        txt = None
        for enc in ("utf-16-le", "utf-8", "latin-1"):
            try:
                t = raw.decode(enc, errors="ignore")
                if len(t) > 1000:
                    txt = t
                    break
            except Exception:
                pass
        if not txt:
            item["layout_parse"] = "no_decodable_text"
            report.append(item)
            continue

        # Intentar parseo JSON directo
        j = None
        try:
            j = json.loads(txt)
            item["layout_parse"] = "json"
        except Exception:
            item["layout_parse"] = "text-only"

        if isinstance(j, dict):
            secs = j.get("sections", []) or []
            item["pages"] = len(secs)
            vc = 0
            for s in secs:
                vc += len(s.get("visualContainers", []) or [])
            item["visual_containers"] = vc

        # búsqueda textual de palabras clave
        pats = [r"gastos?", r"adm", r"operaciones", r"financier"]
        for pat in pats:
            for m in re.finditer(pat, txt, flags=re.IGNORECASE):
                start = max(0, m.start()-60)
                end = min(len(txt), m.end()+90)
                snip = txt[start:end].replace("\n", " ").replace("\r", " ")
                if snip not in item["gastos_hits"]:
                    item["gastos_hits"].append(snip)
                if len(item["gastos_hits"]) >= 8:
                    break
            if len(item["gastos_hits"]) >= 8:
                break
    except Exception as e:
        item["layout_parse"] = f"error: {e}"
    report.append(item)

out = Path(r"C:\Users\josej\.openclaw\workspace\projects\finanzas\index\pbix_layout_scan.json")
out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
print(out)
print(json.dumps(report, ensure_ascii=False, indent=2)[:8000])
