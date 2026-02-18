import argparse
import json
from pathlib import Path


def load_records(path):
    recs = []
    with Path(path).open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            recs.append(json.loads(line))
    return recs


def match_query(rec, q):
    if not q:
        return True
    q = q.lower()
    hay = " ".join([
        str(rec.get("sheet", "")),
        str(rec.get("designation", "")),
        str(rec.get("family", "")),
        json.dumps(rec.get("values", {}), ensure_ascii=False)
    ]).lower()
    return q in hay


def main():
    ap = argparse.ArgumentParser(description="Consulta rápida al índice ICHA")
    ap.add_argument("--index", default="data/icha_catalogo_normalizado.jsonl")
    ap.add_argument("--q", default="", help="Texto a buscar")
    ap.add_argument("--family", default="", help="Familia exacta, ej IN, IP, L")
    ap.add_argument("--limit", type=int, default=10)
    ap.add_argument("--min-peso", type=float, default=None)
    ap.add_argument("--max-peso", type=float, default=None)
    args = ap.parse_args()

    recs = load_records(args.index)
    out = []
    for r in recs:
        if args.family and str(r.get("family", "")).upper() != args.family.upper():
            continue
        p = r.get("peso_kgfm")
        if args.min_peso is not None and (p is None or p < args.min_peso):
            continue
        if args.max_peso is not None and (p is None or p > args.max_peso):
            continue
        if not match_query(r, args.q):
            continue
        out.append(r)

    out = out[: args.limit]
    print(json.dumps({"count": len(out), "results": out}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
