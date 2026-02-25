import argparse
import csv
import hashlib
import json
import re
from datetime import datetime
from pathlib import Path

from pypdf import PdfReader

import sys
sys.path.insert(0, str(Path(__file__).parent))
from rag_utils import normalize_project_code


def norm(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "")).strip()


def chunk_text(text: str, size: int = 1500, overlap: int = 200):
    text = norm(text)
    if not text:
        return []
    chunks = []
    i = 0
    n = len(text)
    while i < n:
        j = min(i + size, n)
        chunks.append(text[i:j])
        if j >= n:
            break
        i = max(0, j - overlap)
    return chunks


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for b in iter(lambda: f.read(1024 * 1024), b""):
            h.update(b)
    return h.hexdigest()


def infer_doc_id(name: str) -> str:
    base = Path(name).stem
    m = re.search(r"([A-Z]{2,5}[-_]?\d{3,5}[-_][A-Z]{2,5}[-_][A-Z]{2,5}[-_]?\d{5,8}(?:[-_]\d+)?)", base, re.IGNORECASE)
    return m.group(1).replace("_", "-").upper() if m else base


def build_tags(project_code: str, custom_tags_csv: str = ""):
    norm = normalize_project_code(project_code)
    tags = [project_code, norm]
    if custom_tags_csv:
        tags.extend([t.strip() for t in custom_tags_csv.split(",") if t.strip()])
    # dedupe preservando orden
    seen = set()
    out = []
    for t in tags:
        if t not in seen:
            out.append(t)
            seen.add(t)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", required=True)
    ap.add_argument("--project", required=True)
    ap.add_argument("--project-code", required=True)
    ap.add_argument("--tags", default="", help="Tags extra CSV (ej: PO-4519,ID-1425)")
    args = ap.parse_args()

    src = Path(args.source)
    project_dir = Path(args.project)
    data_dir = Path("data")
    data_dir.mkdir(parents=True, exist_ok=True)

    pdfs = sorted([p for p in src.rglob("*") if p.is_file() and p.suffix.lower() == ".pdf"])

    docs_out = data_dir / f"{args.project_code.lower()}_docs.jsonl"
    chunks_out = data_dir / f"{args.project_code.lower()}_chunks.jsonl"
    index_csv = project_dir / "INDEX.csv"
    summaries_dir = project_dir / "docs" / "summaries"
    summaries_dir.mkdir(parents=True, exist_ok=True)

    chunk_tags = build_tags(args.project_code, args.tags)

    existing_keys = set()
    if index_csv.exists():
        with index_csv.open("r", encoding="utf-8-sig", newline="") as f:
            r = csv.DictReader(f)
            for row in r:
                k = (row.get("origen", ""), row.get("ruta", ""))
                existing_keys.add(k)

    existing_sources = set()
    if docs_out.exists():
        with docs_out.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    row = json.loads(line)
                    existing_sources.add(row.get("source_path", ""))
                except Exception:
                    continue

    new_index_rows = []
    total_chunks = 0
    indexed_pdfs = 0

    with docs_out.open("a", encoding="utf-8") as fd, chunks_out.open("a", encoding="utf-8") as fc:
        for p in pdfs:
            if str(p) in existing_sources:
                continue

            rel = p.relative_to(src)
            doc_id = infer_doc_id(p.name)
            sha = sha256_file(p)
            mtime = datetime.fromtimestamp(p.stat().st_mtime).isoformat(timespec="seconds")

            page_texts = []
            page_count = 0
            try:
                reader = PdfReader(str(p))
                page_count = len(reader.pages)
                for idx, pg in enumerate(reader.pages, start=1):
                    txt = norm(pg.extract_text() or "")
                    page_texts.append((idx, txt))
            except Exception as e:
                page_texts = [(1, "")]
                doc_err = str(e)
            else:
                doc_err = None

            full_text = "\n".join(t for _, t in page_texts if t)
            summary = full_text[:1200]

            doc_row = {
                "project": args.project_code,
                "doc_id": doc_id,
                "filename": p.name,
                "source_path": str(p),
                "source_rel": str(rel).replace("\\", "/"),
                "pages": page_count,
                "bytes": p.stat().st_size,
                "sha256": sha,
                "modified_at": mtime,
                "extract_status": "ok" if not doc_err else "error",
                "extract_error": doc_err,
            }
            fd.write(json.dumps(doc_row, ensure_ascii=False) + "\n")
            indexed_pdfs += 1

            sm = summaries_dir / f"{doc_id}.md"
            with sm.open("w", encoding="utf-8") as fs:
                fs.write(f"# {doc_id}\n\n")
                fs.write(f"- Archivo: {p.name}\n")
                fs.write(f"- Ruta origen: {p}\n")
                fs.write(f"- Páginas: {page_count}\n")
                fs.write(f"- Estado extracción: {doc_row['extract_status']}\n\n")
                fs.write("## Resumen preliminar (auto)\n\n")
                fs.write((summary if summary else "Sin texto extraíble (posible PDF escaneado).") + "\n")

            for pg, txt in page_texts:
                for i, ch in enumerate(chunk_text(txt), start=1):
                    total_chunks += 1
                    ck = {
                        "project": args.project_code,
                        "doc_id": doc_id,
                        "page": pg,
                        "chunk": i,
                        "text": ch,
                        "source_path": str(p),
                        "tags": chunk_tags,
                    }
                    fc.write(json.dumps(ck, ensure_ascii=False) + "\n")

            idx_key = ("onedrive", str(p))
            if idx_key not in existing_keys:
                new_index_rows.append({
                    "tipo": "doc",
                    "fecha": datetime.now().date().isoformat(),
                    "origen": "onedrive",
                    "id_ref": doc_id,
                    "titulo": p.name,
                    "version": "",
                    "estado": "activo",
                    "ruta": str(p),
                    "hash": sha,
                    "observaciones": f"pages={page_count}; extract={doc_row['extract_status']}",
                })

    fieldnames = ["tipo", "fecha", "origen", "id_ref", "titulo", "version", "estado", "ruta", "hash", "observaciones"]
    write_header = not index_csv.exists()
    with index_csv.open("a", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        if write_header:
            w.writeheader()
        for row in new_index_rows:
            w.writerow(row)

    print(json.dumps({
        "project": args.project_code,
        "pdf_found": len(pdfs),
        "pdf_indexed": indexed_pdfs,
        "new_index_rows": len(new_index_rows),
        "chunks_added": total_chunks,
        "docs_jsonl": str(docs_out),
        "chunks_jsonl": str(chunks_out),
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
