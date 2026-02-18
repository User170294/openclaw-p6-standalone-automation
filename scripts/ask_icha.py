import argparse
import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


def load_records(path: str) -> List[Dict[str, Any]]:
    recs = []
    with Path(path).open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                recs.append(json.loads(line))
    return recs


def to_float(v: Any) -> Optional[float]:
    if isinstance(v, (int, float)):
        return float(v)
    if isinstance(v, str):
        s = v.strip().replace(",", ".")
        try:
            return float(s)
        except Exception:
            return None
    return None


def extract_metric(values: Dict[str, Any], metric: str) -> Optional[float]:
    # Busca por claves que contengan el token de métrica y valor numérico
    token = metric.lower()
    candidates = []
    for k, v in values.items():
        if not isinstance(k, str):
            continue
        lk = k.lower()
        if token in lk:
            num = to_float(v)
            if num is not None:
                candidates.append(num)
    if not candidates:
        return None
    # para W/I/i podemos tener más de un eje; devolvemos el máximo por utilidad de filtrado
    return max(candidates)


def parse_family(text: str) -> Optional[str]:
    families = ["IN", "IP", "HN", "PH", "TL", "XL", "IC", "ICA", "CA", "C", "L", "T"]
    up = text.upper()
    # priorizar tokens largos
    families = sorted(families, key=len, reverse=True)
    for f in families:
        if re.search(rf"\b{re.escape(f)}\b", up):
            return f
    return None


def parse_designation(text: str) -> Optional[str]:
    # Ej: IN 100, TL 20*30, C 30 (solo familias válidas)
    fam = parse_family(text)
    if not fam:
        return None
    m = re.search(rf"\b{re.escape(fam)}\s*(\d{{2,4}}(?:\s*\*\s*\d{{1,4}})?)", text, flags=re.IGNORECASE)
    if not m:
        return None
    return f"{fam} {m.group(1).replace(' ', '')}"


def parse_bounds(text: str, field_words: List[str]) -> Tuple[Optional[float], Optional[float]]:
    low = high = None
    t = text.lower()
    field_re = "(?:" + "|".join(re.escape(w) for w in field_words) + ")"

    # entre X y Y
    m = re.search(rf"{field_re}[^\d]{{0,25}}entre\s+([0-9]+(?:[\.,][0-9]+)?)\s+y\s+([0-9]+(?:[\.,][0-9]+)?)", t)
    if m:
        a = float(m.group(1).replace(",", "."))
        b = float(m.group(2).replace(",", "."))
        return (min(a, b), max(a, b))

    # mayor / mínimo
    m = re.search(rf"{field_re}[^\d]{0,25}(?:>|>=|mayor(?:\s+a)?(?:\s+o\s+igual)?|sobre|mínim[oa])\s*([0-9]+(?:[\.,][0-9]+)?)", t)
    if m:
        low = float(m.group(1).replace(",", "."))

    # menor / máximo
    m = re.search(rf"{field_re}[^\d]{0,25}(?:<|<=|menor(?:\s+a)?(?:\s+o\s+igual)?|bajo|máxim[oa])\s*([0-9]+(?:[\.,][0-9]+)?)", t)
    if m:
        high = float(m.group(1).replace(",", "."))

    # fallback compacto: "peso < 300"
    if low is None and high is None:
        m = re.search(rf"{field_re}\s*(<=|>=|<|>)\s*([0-9]+(?:[\.,][0-9]+)?)", t)
        if m:
            op = m.group(1)
            val = float(m.group(2).replace(",", "."))
            if op in (">", ">="):
                low = val
            else:
                high = val

    return low, high


def apply_query(records: List[Dict[str, Any]], ask: str, limit: int) -> Dict[str, Any]:
    family = parse_family(ask)
    designation_hint = parse_designation(ask)

    peso_min, peso_max = parse_bounds(ask, ["peso", "kgf/m", "kgfm"])
    w_min, w_max = parse_bounds(ask, ["w", "módulo resistente", "modulo resistente"])
    # fallback robusto para 'W mayor/menor a ...'
    if w_min is None and w_max is None:
        t = ask.lower()
        m = re.search(r"\bw\b\s*(?:>|>=|mayor(?:\s+a)?(?:\s+o\s+igual)?|sobre)\s*([0-9]+(?:[\.,][0-9]+)?)", t)
        if m:
            w_min = float(m.group(1).replace(",", "."))
        m = re.search(r"\bw\b\s*(?:<|<=|menor(?:\s+a)?(?:\s+o\s+igual)?|bajo|máxim[oa])\s*([0-9]+(?:[\.,][0-9]+)?)", t)
        if m:
            w_max = float(m.group(1).replace(",", "."))

    i_min, i_max = parse_bounds(ask, ["inercia", "ix", "iy", "i x", "i y"])

    out = []
    for r in records:
        if family and str(r.get("family", "")).upper() != family:
            continue

        designation = str(r.get("designation") or "")
        if designation_hint:
            # match flexible: IN100 ~ IN 100*
            norm_d = re.sub(r"\s+", "", designation.upper())
            norm_h = re.sub(r"\s+", "", designation_hint.upper())
            if norm_h not in norm_d:
                # si no calza exacto, sigue igual (consulta puede ser amplia)
                pass

        peso = to_float(r.get("peso_kgfm"))
        w = extract_metric(r.get("values", {}), "w")
        inertia = extract_metric(r.get("values", {}), "i")

        if peso_min is not None and (peso is None or peso < peso_min):
            continue
        if peso_max is not None and (peso is None or peso > peso_max):
            continue
        if w_min is not None and (w is None or w < w_min):
            continue
        if w_max is not None and (w is None or w > w_max):
            continue
        if i_min is not None and (inertia is None or inertia < i_min):
            continue
        if i_max is not None and (inertia is None or inertia > i_max):
            continue

        text_hay = " ".join([
            str(r.get("sheet", "")),
            str(r.get("designation", "")),
            str(r.get("family", "")),
            json.dumps(r.get("values", {}), ensure_ascii=False),
        ]).lower()
        # si hay términos claros, filtra por ellos
        keywords = [k for k in re.findall(r"[a-zA-ZáéíóúñÁÉÍÓÚÑ0-9*]+", ask.lower()) if len(k) > 2]
        if keywords:
            score = sum(1 for k in keywords if k in text_hay)
        else:
            score = 0

        out.append({
            "sheet": r.get("sheet"),
            "row": r.get("row"),
            "family": r.get("family"),
            "designation": r.get("designation"),
            "peso_kgfm": peso,
            "w_ref": w,
            "i_ref": inertia,
            "score": score,
            "values": r.get("values", {}),
        })

    out.sort(key=lambda x: (x["score"], x["w_ref"] or -1, -(x["peso_kgfm"] or 0)), reverse=True)
    out = out[:limit]

    return {
        "query": ask,
        "parsed": {
            "family": family,
            "designation_hint": designation_hint,
            "peso_min": peso_min,
            "peso_max": peso_max,
            "w_min": w_min,
            "w_max": w_max,
            "i_min": i_min,
            "i_max": i_max,
        },
        "count": len(out),
        "results": out,
    }


def main():
    ap = argparse.ArgumentParser(description="Consulta en lenguaje natural para índice ICHA")
    ap.add_argument("--ask", required=True, help="Consulta natural, ej: 'dame perfiles IN con peso < 320 y W mayor a 1700'")
    ap.add_argument("--index", default="data/icha_catalogo_normalizado.jsonl")
    ap.add_argument("--limit", type=int, default=10)
    args = ap.parse_args()

    recs = load_records(args.index)
    result = apply_query(recs, args.ask, args.limit)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
