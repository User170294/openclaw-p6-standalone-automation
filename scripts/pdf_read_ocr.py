import argparse
import json
from pathlib import Path

import fitz  # pymupdf


def extract_direct_text(doc: fitz.Document) -> list[dict]:
    pages = []
    for i, page in enumerate(doc, start=1):
        txt = page.get_text("text") or ""
        pages.append({"page": i, "method": "text", "chars": len(txt), "text": txt})
    return pages


def ocr_page(page: fitz.Page, ocr_engine, dpi: int = 220) -> str:
    mat = fitz.Matrix(dpi / 72, dpi / 72)
    pix = page.get_pixmap(matrix=mat, alpha=False)
    import numpy as np

    img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
    result, _ = ocr_engine(img)
    if not result:
        return ""
    lines = []
    for row in result:
        try:
            lines.append(row[1])
        except Exception:
            pass
    return "\n".join(lines)


def ensure_ocr_engine():
    from rapidocr_onnxruntime import RapidOCR

    return RapidOCR()


def run(pdf_path: Path, out_dir: Path, ocr_threshold: int, ocr_max_pages: int) -> dict:
    doc = fitz.open(pdf_path)
    pages = extract_direct_text(doc)

    # OCR fallback when page is mostly image/no text
    ocr_engine = None
    ocr_count = 0
    for p in pages:
        if p["chars"] >= ocr_threshold:
            continue
        if ocr_count >= ocr_max_pages:
            continue
        if ocr_engine is None:
            ocr_engine = ensure_ocr_engine()
        txt = ocr_page(doc[p["page"] - 1], ocr_engine)
        if txt.strip():
            p["method"] = "ocr"
            p["chars"] = len(txt)
            p["text"] = txt
        ocr_count += 1

    full_text = "\n\n".join([f"## Página {p['page']} ({p['method']})\n{p['text']}" for p in pages if p["text"].strip()])

    out_dir.mkdir(parents=True, exist_ok=True)
    stem = pdf_path.stem
    md_path = out_dir / f"{stem}.md"
    json_path = out_dir / f"{stem}.json"

    md_path.write_text(full_text, encoding="utf-8")
    json_path.write_text(json.dumps({"file": str(pdf_path), "pages": pages}, ensure_ascii=False, indent=2), encoding="utf-8")

    return {
        "file": str(pdf_path),
        "pages": len(pages),
        "ocr_pages": sum(1 for p in pages if p["method"] == "ocr"),
        "chars_total": sum(p["chars"] for p in pages),
        "md": str(md_path),
        "json": str(json_path),
    }


def main():
    ap = argparse.ArgumentParser(description="Extract text from PDF with OCR fallback")
    ap.add_argument("pdfs", nargs="+", help="PDF paths")
    ap.add_argument("--out", default="data/pdf_extract", help="Output dir")
    ap.add_argument("--ocr-threshold", type=int, default=120, help="If direct text chars < threshold, run OCR")
    ap.add_argument("--ocr-max-pages", type=int, default=30, help="Max OCR pages per PDF")
    args = ap.parse_args()

    out_dir = Path(args.out)
    results = []
    for p in args.pdfs:
        results.append(run(Path(p), out_dir, args.ocr_threshold, args.ocr_max_pages))

    print(json.dumps(results, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()