import json
from pathlib import Path

base = Path(r"C:\Users\josej\.openclaw\workspace")
idx = base / "projects" / "finanzas" / "index"
out = base / "data" / "finanzas_chunks.jsonl"
out.parent.mkdir(parents=True, exist_ok=True)

excel = json.loads((idx / "excel_index.json").read_text(encoding="utf-8"))
pbix = json.loads((idx / "pbix_index.json").read_text(encoding="utf-8"))

lines = []

for i, f in enumerate(excel, 1):
    sheets = f.get("sheets", [])
    tables = []
    for s in sheets:
        tables.extend(s.get("tables", []) or [])
    filas_tot = sum((s.get("rows", 0) or 0) for s in sheets)
    cols_max = max([s.get("cols", 0) or 0 for s in sheets] or [0])
    formulas_tot = sum((s.get("formula_cells", 0) or 0) for s in sheets)
    tablas_txt = ", ".join(sorted(set(t for t in tables if t))[:20]) if tables else "ninguna"
    hojas_det = "; ".join(
        f"{s.get('name', '?')}:{s.get('rows', 0)}x{s.get('cols', 0)} f={s.get('formula_cells', 0)}"
        for s in sheets[:20]
    )
    txt = (
        f"Excel {f.get('name', '')} | hojas={f.get('sheet_count', 0)} | filas_tot={filas_tot} "
        f"| cols_max={cols_max} | formulas_tot={formulas_tot} | tablas={tablas_txt} "
        f"| hojas_detalle={hojas_det}"
    )
    obj = {
        "project": "finanzas",
        "doc_id": Path(f.get("name", f"excel_{i}")).stem,
        "page": 1,
        "chunk": 1,
        "text": txt,
        "source_path": f.get("file", ""),
        "tags": ["finanzas", "excel"],
    }
    lines.append(json.dumps(obj, ensure_ascii=False))

for i, f in enumerate(pbix, 1):
    entries = f.get("zip_entries", [])
    txt = (
        f"PBIX {f.get('name', '')} | size={f.get('size', 0)} | datamodel={f.get('has_datamodel', False)} "
        f"| layout={f.get('has_layout', False)} | connections={f.get('has_connections', False)} "
        f"| entries={', '.join(entries[:20])}"
    )
    obj = {
        "project": "finanzas",
        "doc_id": Path(f.get("name", f"pbix_{i}")).stem,
        "page": 1,
        "chunk": 1,
        "text": txt,
        "source_path": f.get("file", ""),
        "tags": ["finanzas", "pbix"],
    }
    lines.append(json.dumps(obj, ensure_ascii=False))

out.write_text("\n".join(lines) + "\n", encoding="utf-8")
print(f"wrote {len(lines)} chunks to {out}")
