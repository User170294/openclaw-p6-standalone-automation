"""
rag_utils.py
Utilidades compartidas para RAG semántico de proyectos.
"""

from typing import Any, Dict, List

# Cache de modelos en memoria
_RERANK_MODEL_CACHE: Dict[str, Any] = {}

RERANK_MODEL_NAME = "cross-encoder/ms-marco-MiniLM-L-6-v2"


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
