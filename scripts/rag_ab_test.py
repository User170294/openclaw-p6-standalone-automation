import json
import os
import re
import subprocess
import sys
from statistics import mean

QUERIES = [
    "esquema de pintura bandejas",
    "hitos entrega marzo",
    "cambio soldado apernado",
]

# Reglas simples de relevancia por query (puedes ajustar)
RELEVANCE_RULES = {
    "esquema de pintura bandejas": [
        r"pintura", r"esquema", r"coating", r"dft", r"a-3", r"bandej"
    ],
    "hitos entrega marzo": [
        r"hito", r"marzo", r"w0\d", r"pms", r"programa", r"entrega", r"fecha"
    ],
    "cambio soldado apernado": [
        r"soldad", r"apernad", r"conexi", r"terreno", r"taller", r"rfi"
    ],
}


def run_query(query: str, hybrid: bool):
    cmd = [
        sys.executable,
        "scripts/search_project.py",
        "--project",
        "1844",
        "--ask",
        query,
        "--top",
        "3",
        "--json",
    ]
    cmd += ["--hybrid"] if hybrid else ["--no-hybrid"]

    env = os.environ.copy()
    env["PYTHONUTF8"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"

    p = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=env,
    )
    merged = (p.stdout or "") + "\n" + (p.stderr or "")
    rows = extract_last_json_array(merged)
    return rows, p.returncode


def extract_last_json_array(text: str):
    # Busca cualquier '[' y prueba raw_decode para extraer un array JSON aunque haya logs después.
    decoder = json.JSONDecoder()
    starts = [m.start() for m in re.finditer(r"\[", text)]
    for s in starts:
        try:
            data, _ = decoder.raw_decode(text[s:])
            if isinstance(data, list):
                return data
        except Exception:
            continue
    return []


def is_relevant(query: str, row: dict) -> bool:
    pats = RELEVANCE_RULES.get(query, [])
    bag = " ".join([
        str(row.get("doc_id", "")),
        str(row.get("text", "")),
        " ".join(row.get("tags", []) if isinstance(row.get("tags"), list) else []),
    ]).lower()
    return any(re.search(p, bag) for p in pats)


def avg_rerank(rows):
    vals = [float(r.get("rerank_score", 0.0)) for r in rows if "rerank_score" in r]
    return round(mean(vals), 4) if vals else 0.0


def relevant_at_k(query: str, rows, k=3):
    top = rows[:k]
    if not top:
        return 0.0
    rel = sum(1 for r in top if is_relevant(query, r))
    return round(rel / k, 4)


def print_mode(title, rows, code, query):
    print(f"  {title} rc={code} avg_rerank={avg_rerank(rows)} rel@3={relevant_at_k(query, rows, 3)}")
    for i, r in enumerate(rows[:3], 1):
        rr = r.get("rerank_score", None)
        rel = "REL" if is_relevant(query, r) else "NOREL"
        rr_txt = f" rerank={rr:.4f}" if isinstance(rr, (int, float)) else ""
        print(f"    {i}. {r.get('doc_id','?')} p{r.get('page','?')}{rr_txt} {rel}")


def main():
    print("A/B RAG OT-1844 (top-3) — métrica: avg_rerank + rel@3\n")
    for q in QUERIES:
        h_rows, h_code = run_query(q, hybrid=True)
        v_rows, v_code = run_query(q, hybrid=False)

        print(f"Query: {q}")
        print_mode("HYBRID", h_rows, h_code, q)
        print_mode("VECTOR", v_rows, v_code, q)

        h_rel = relevant_at_k(q, h_rows, 3)
        v_rel = relevant_at_k(q, v_rows, 3)
        delta = round(h_rel - v_rel, 4)
        print(f"  Delta rel@3 (HYBRID - VECTOR): {delta:+.4f}")
        print("-" * 88)


if __name__ == "__main__":
    main()
