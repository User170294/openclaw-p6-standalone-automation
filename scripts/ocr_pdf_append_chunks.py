import argparse
import json
from pathlib import Path

import numpy as np
import pypdfium2 as pdfium
from rapidocr_onnxruntime import RapidOCR


def norm(s: str) -> str:
    return " ".join((s or "").split())


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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pdf", required=True)
    ap.add_argument("--project", required=True)
    ap.add_argument("--doc-id", required=True)
    ap.add_argument("--chunks-jsonl", required=True)
    ap.add_argument("--tags", default="")
    ap.add_argument("--dpi", type=int, default=250)
    args = ap.parse_args()

    pdf_path = Path(args.pdf)
    chunks_path = Path(args.chunks_jsonl)
    tags = [t.strip() for t in args.tags.split(",") if t.strip()]

    ocr = RapidOCR()
    pdf = pdfium.PdfDocument(str(pdf_path))

    total_chunks = 0
    pages_with_text = 0

    with chunks_path.open("a", encoding="utf-8") as out:
        for page_index in range(len(pdf)):
            page = pdf[page_index]
            bitmap = page.render(scale=args.dpi / 72).to_pil()
            img = np.array(bitmap)
            result, _ = ocr(img)
            lines = []
            if result:
                for item in result:
                    if len(item) >= 2 and item[1]:
                        lines.append(item[1])
            text = norm(" ".join(lines))
            if not text:
                continue
            pages_with_text += 1
            for i, ch in enumerate(chunk_text(text), start=1):
                row = {
                    "project": args.project,
                    "doc_id": args.doc_id,
                    "page": page_index + 1,
                    "chunk": i,
                    "text": ch,
                    "source_path": str(pdf_path),
                    "tags": tags,
                }
                out.write(json.dumps(row, ensure_ascii=False) + "\n")
                total_chunks += 1

    print(json.dumps({
        "pdf": str(pdf_path),
        "pages": len(pdf),
        "pages_with_text": pages_with_text,
        "chunks_added": total_chunks,
        "chunks_jsonl": str(chunks_path),
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
