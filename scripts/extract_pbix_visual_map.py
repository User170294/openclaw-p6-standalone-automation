import json, zipfile, csv
from pathlib import Path

base = Path(r"C:\Users\josej\OneDrive\002 SIMTEXX\000_Control de Porcesos\004_Informe M.Munizaga")
out_json = Path(r"C:\Users\josej\.openclaw\workspace\projects\finanzas\index\pbix_visual_field_map.json")
out_csv  = Path(r"C:\Users\josej\.openclaw\workspace\projects\finanzas\index\pbix_visual_field_map.csv")

records = []

def extract_queryrefs(config_obj):
    refs = []
    entities = set()
    def walk(o):
        if isinstance(o, dict):
            for k,v in o.items():
                if k == "queryRef" and isinstance(v, str):
                    refs.append(v)
                if k == "Entity" and isinstance(v, str):
                    entities.add(v)
                walk(v)
        elif isinstance(o, list):
            for i in o:
                walk(i)
    walk(config_obj)
    return sorted(set(refs)), sorted(entities)

for pbix in sorted(base.glob("*.pbix")):
    with zipfile.ZipFile(pbix, "r") as z:
        raw = z.read("Report/Layout")
    text = raw.decode("utf-16-le", errors="ignore")
    layout = json.loads(text)

    sections = layout.get("sections", []) or []
    for s_idx, sec in enumerate(sections):
        page_name = sec.get("displayName") or sec.get("name") or f"Page_{s_idx+1}"
        visuals = sec.get("visualContainers", []) or []
        for v_idx, vc in enumerate(visuals):
            cfg_raw = vc.get("config")
            if not isinstance(cfg_raw, str) or not cfg_raw.strip().startswith("{"):
                continue
            try:
                cfg = json.loads(cfg_raw)
            except Exception:
                continue

            single = cfg.get("singleVisual", {}) or {}
            vtype = single.get("visualType") or "unknown"
            title = ""
            try:
                title = single.get("vcObjects", {}).get("title", {}).get("properties", {}).get("text", {}).get("expr", {}).get("Literal", {}).get("Value", "")
                if isinstance(title, str):
                    title = title.strip("\"")
            except Exception:
                title = ""

            refs, entities = extract_queryrefs(cfg)
            rec = {
                "pbix": pbix.name,
                "page": page_name,
                "visual_index": v_idx,
                "visual_type": vtype,
                "title": title,
                "entities": entities,
                "query_refs": refs,
            }
            records.append(rec)

out_json.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")

with out_csv.open("w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["pbix","page","visual_index","visual_type","title","entities","query_refs"])
    for r in records:
        w.writerow([
            r["pbix"], r["page"], r["visual_index"], r["visual_type"], r["title"],
            " | ".join(r["entities"]), " | ".join(r["query_refs"])
        ])

print(f"records={len(records)}")
print(out_json)
print(out_csv)
