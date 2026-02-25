"""
rag_utils.py
Utilidades compartidas para RAG semántico de proyectos.
"""

import math
import json
import hashlib
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, List, Tuple, Optional

# Cache de modelos en memoria
_RERANK_MODEL_CACHE: Dict[str, Any] = {}

RERANK_MODEL_NAME = "cross-encoder/ms-marco-MiniLM-L-6-v2"
DEFAULT_TOP_K = 10

BM25_CACHE_DIR = Path("data/bm25_cache")
BM25_CACHE_DIR.mkdir(parents=True, exist_ok=True)


def normalize_project_code(project: str) -> str:
    """Normaliza código de proyecto (ej: 1844 -> OT-1844)."""
    p = (project or "").strip().upper()
    if not p:
        return p
    if p.isdigit():
        return f"OT-{p}"
    if p.startswith("OT") and not p.startswith("OT-") and len(p) > 2:
        suffix = p[2:]
        if suffix.isdigit():
            return f"OT-{suffix}"
    return p


def collection_name_from_project(project: str) -> str:
    """Nombre de colección Chroma consistente para un proyecto."""
    return normalize_project_code(project).lower().replace("-", "_")


def get_reranker_model(model_name: str = RERANK_MODEL_NAME):
    """Carga y cachea el modelo de reranking."""
    if model_name in _RERANK_MODEL_CACHE:
        return _RERANK_MODEL_CACHE[model_name]
    from sentence_transformers import CrossEncoder
    model = CrossEncoder(model_name)
    _RERANK_MODEL_CACHE[model_name] = model
    return model


def tokenize(text: str) -> List[str]:
    """Tokenización simple y robusta para recuperación léxica."""
    return re.findall(r"\w+", (text or "").lower(), flags=re.UNICODE)


def bm25_rank(query: str, docs: List[str], k1: float = 1.5, b: float = 0.75) -> List[Tuple[int, float]]:
    """Ranking BM25 puro (sin dependencias externas)."""
    if not docs:
        return []

    tokenized_docs = [tokenize(d) for d in docs]
    doc_lens = [len(toks) for toks in tokenized_docs]
    avgdl = sum(doc_lens) / max(1, len(doc_lens))

    df = defaultdict(int)
    for toks in tokenized_docs:
        for t in set(toks):
            df[t] += 1

    N = len(docs)
    q_terms = tokenize(query)
    q_tf = Counter(q_terms)

    ranked: List[Tuple[int, float]] = []
    for i, toks in enumerate(tokenized_docs):
        tf = Counter(toks)
        score = 0.0
        for term, qf in q_tf.items():
            if term not in tf:
                continue
            n_qi = df.get(term, 0)
            idf = math.log(1 + (N - n_qi + 0.5) / (n_qi + 0.5))
            f = tf[term]
            denom = f + k1 * (1 - b + b * (doc_lens[i] / max(avgdl, 1e-9)))
            score += idf * ((f * (k1 + 1)) / max(denom, 1e-9)) * qf
        ranked.append((i, score))

    ranked.sort(key=lambda x: x[1], reverse=True)
    return ranked


def _bm25_cache_path(collection_name: str) -> Path:
    safe = re.sub(r"[^a-zA-Z0-9_.-]", "_", collection_name)
    return BM25_CACHE_DIR / f"{safe}.bm25.json"


def docs_md5_signature(docs: List[str], sample_size: int = 50) -> str:
    h = hashlib.md5()
    for d in docs[:sample_size]:
        s = (d or "").strip().encode("utf-8", errors="ignore")
        h.update(s)
        h.update(b"\n")
    return h.hexdigest()


def build_bm25_index(docs: List[str]) -> Dict[str, Any]:
    tokenized_docs = [tokenize(d) for d in docs]
    doc_lens = [len(toks) for toks in tokenized_docs]
    avgdl = (sum(doc_lens) / len(doc_lens)) if doc_lens else 0.0

    df = defaultdict(int)
    for toks in tokenized_docs:
        for t in set(toks):
            df[t] += 1

    return {
        "N": len(docs),
        "doc_lens": doc_lens,
        "avgdl": avgdl,
        "df": dict(df),
        "tokenized_docs": tokenized_docs,
    }


def save_bm25_index(collection_name: str, doc_count: int, docs_sig_md5: str, bm25_index: Dict[str, Any]) -> None:
    payload = {
        "collection": collection_name,
        "doc_count": doc_count,
        "docs_sig_md5": docs_sig_md5,
        "bm25": bm25_index,
    }
    with _bm25_cache_path(collection_name).open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False)


def load_bm25_index_if_valid(collection_name: str, doc_count: int, docs_sig_md5: str) -> Optional[Dict[str, Any]]:
    p = _bm25_cache_path(collection_name)
    if not p.exists():
        return None
    try:
        payload = json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None

    if payload.get("doc_count") != doc_count:
        return None
    if payload.get("docs_sig_md5") != docs_sig_md5:
        return None
    return payload.get("bm25")


def get_or_build_bm25_index(collection_name: str, docs: List[str]) -> Dict[str, Any]:
    doc_count = len(docs)
    sig = docs_md5_signature(docs, sample_size=50)
    cached = load_bm25_index_if_valid(collection_name, doc_count, sig)
    if cached is not None:
        return cached
    idx = build_bm25_index(docs)
    save_bm25_index(collection_name, doc_count, sig, idx)
    return idx


def bm25_rank_from_index(query: str, index: Dict[str, Any], k1: float = 1.5, b: float = 0.75) -> List[Tuple[int, float]]:
    N = int(index.get("N", 0))
    if N == 0:
        return []
    tokenized_docs = index["tokenized_docs"]
    doc_lens = index["doc_lens"]
    avgdl = float(index.get("avgdl", 0.0)) or 1e-9
    df = index["df"]
    q_tf = Counter(tokenize(query))

    ranked: List[Tuple[int, float]] = []
    for i, toks in enumerate(tokenized_docs):
        tf = Counter(toks)
        score = 0.0
        for term, qf in q_tf.items():
            f = tf.get(term, 0)
            if not f:
                continue
            n_qi = df.get(term, 0)
            idf = math.log(1 + (N - n_qi + 0.5) / (n_qi + 0.5))
            denom = f + k1 * (1 - b + b * (doc_lens[i] / avgdl))
            score += idf * ((f * (k1 + 1)) / max(denom, 1e-9)) * qf
        ranked.append((i, score))
    ranked.sort(key=lambda x: x[1], reverse=True)
    return ranked


def rrf_fuse(rank_lists: List[List[int]], k: int = 60) -> List[Tuple[int, float]]:
    """Reciprocal Rank Fusion para combinar rankings heterogéneos."""
    scores = defaultdict(float)
    for ranking in rank_lists:
        for r, idx in enumerate(ranking, start=1):
            scores[idx] += 1.0 / (k + r)
    fused = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    return fused


def rerank_chunks(query: str, chunks: List[Dict[str, Any]], reranker) -> List[Dict[str, Any]]:
    """
    Rerankea chunks con CrossEncoder.

    Args:
        query: consulta del usuario
        chunks: lista de dicts con al menos {'text': str, ...}
        reranker: modelo CrossEncoder cargado

    Returns:
        Lista de chunks ordenados por rerank_score descendente (añade campo 'rerank_score')
    """
    if not chunks:
        return chunks

    pairs = [(query, ch.get("text", "")) for ch in chunks]
    scores = reranker.predict(pairs)

    rescored = []
    for ch, s in zip(chunks, scores):
        c = dict(ch)
        c["rerank_score"] = float(s)
        rescored.append(c)

    rescored.sort(key=lambda x: x.get("rerank_score", -1e9), reverse=True)
    return rescored
