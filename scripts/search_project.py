"""
search_project.py
Búsqueda semántica sobre chunks de proyecto en ChromaDB.

Uso:
    python scripts/search_project.py --project OT-1844 --ask "requisitos de pintura zinc inorgánico"
    python scripts/search_project.py --project OT-1844 --ask "filete mínimo soldadura" --top 5
    python scripts/search_project.py --project OT-1844 --ask "cronograma semana 8" --tags cronograma,PMS
    python scripts/search_project.py --project OT-1844 --ask "..." --json
"""

import argparse
import json
import sys
from pathlib import Path

CHROMA_DIR   = Path("data/chroma")
MODEL_NAME   = "paraphrase-multilingual-mpnet-base-v2"
DEFAULT_TOP  = 10
PREVIEW_CHARS = 400


def fmt_result(i: int, doc: str, meta: dict, dist: float, rerank_score: float = None) -> str:
    tags    = meta.get("tags", "")
    doc_id  = meta.get("doc_id", "?")
    page    = meta.get("page", "?")
    score   = 1 - dist  # cosine similarity (ChromaDB devuelve distancia)
    preview = doc[:PREVIEW_CHARS].replace("\n", " ")
    if len(doc) > PREVIEW_CHARS:
        preview += "…"
    
    score_line = f"score: {score:.3f}"
    if rerank_score is not None:
        score_line += f"  |  rerank: {rerank_score:.4f}"
    
    return (
        f"\n{'─'*60}\n"
        f"[{i}] {doc_id}  |  pág. {page}  |  {score_line}\n"
        f"    tags: {tags}\n"
        f"    {preview}\n"
    )


def main():
    ap = argparse.ArgumentParser(description="Búsqueda semántica en chunks de proyecto")
    ap.add_argument("--project",    required=True, help="Código de proyecto (ej. OT-1844)")
    ap.add_argument("--ask",        required=True, help="Consulta en lenguaje natural")
    ap.add_argument("--top",        type=int, default=DEFAULT_TOP, help="Número de resultados")
    ap.add_argument("--tags",       default="", help="Filtrar por tags (csv), ej: pintura,coating")
    ap.add_argument("--doc",        default="", help="Filtrar por doc_id (substring)")
    ap.add_argument("--json",       action="store_true", help="Output en JSON")
    ap.add_argument("--no-rerank",  action="store_true", help="Desactivar reranking (solo embeddings)")
    ap.add_argument("--model",      default=MODEL_NAME)
    ap.add_argument("--chroma-dir", default=str(CHROMA_DIR))
    args = ap.parse_args()

    # ── Imports ──────────────────────────────────────────────────────────────
    try:
        import chromadb
        from sentence_transformers import SentenceTransformer
    except ImportError as e:
        print(f"❌ {e} — ejecuta: pip install sentence-transformers chromadb")
        sys.exit(1)
    
    # Importar utilidades de reranking
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent))
    from rag_utils import get_reranker_model, rerank_chunks, normalize_project_code, collection_name_from_project

    # ── Conexión ChromaDB ─────────────────────────────────────────────────────
    chroma_path = Path(args.chroma_dir)
    if not chroma_path.exists():
        print(f"❌ ChromaDB no encontrado en {chroma_path}. Ejecuta primero embed_chunks.py.")
        sys.exit(1)

    client = chromadb.PersistentClient(path=str(chroma_path))
    project_norm = normalize_project_code(args.project)
    collection_name = collection_name_from_project(project_norm)
    try:
        collection = client.get_collection(collection_name)
    except Exception:
        print(f"❌ Colección '{collection_name}' no existe. Ejecuta embed_chunks.py primero.")
        if project_norm != args.project:
            print(f"   (normalizado desde '{args.project}' a '{project_norm}')")
        sys.exit(1)

    # ── Embed query ───────────────────────────────────────────────────────────
    model = SentenceTransformer(args.model)
    q_embedding = model.encode([args.ask]).tolist()

    # ── Filtros opcionales ────────────────────────────────────────────────────
    where = None
    tag_list = [t.strip() for t in args.tags.split(",") if t.strip()]
    if tag_list:
        # ChromaDB where: busca tags que contengan cualquiera de los valores
        # Usamos $contains sobre el campo tags (string csv)
        conditions = [{"tags": {"$contains": t}} for t in tag_list]
        where = {"$or": conditions} if len(conditions) > 1 else conditions[0]

    # ── Consulta ──────────────────────────────────────────────────────────────
    query_kwargs = dict(
        query_embeddings=q_embedding,
        n_results=min(args.top, collection.count()),
        include=["documents", "metadatas", "distances"],
    )
    if where:
        query_kwargs["where"] = where

    results = collection.query(**query_kwargs)

    docs      = results["documents"][0]
    metadatas = results["metadatas"][0]
    distances = results["distances"][0]

    # ── Filtro post-query por doc_id (substring) ──────────────────────────────
    if args.doc:
        filtered = [
            (d, m, dist)
            for d, m, dist in zip(docs, metadatas, distances)
            if args.doc.lower() in m.get("doc_id", "").lower()
        ]
        docs, metadatas, distances = zip(*filtered) if filtered else ([], [], [])

    # ── Reranking (si no está desactivado) ────────────────────────────────────
    rerank_scores = None
    if not args.no_rerank and docs:
        reranker = get_reranker_model()
        chunks_for_rerank = [
            {
                "text": d,
                "doc_id": m.get("doc_id"),
                "page": m.get("page"),
                "tags": m.get("tags", "").split(","),
                "score": 1 - dist,
                "distance": dist,
            }
            for d, m, dist in zip(docs, metadatas, distances)
        ]
        reranked = rerank_chunks(args.ask, chunks_for_rerank, reranker)
        
        # Reordenar docs, metadatas, distances según el nuevo orden
        docs = [ch["text"] for ch in reranked]
        metadatas = [{"doc_id": ch["doc_id"], "page": ch["page"], "tags": ",".join(ch["tags"])} for ch in reranked]
        distances = [ch["distance"] for ch in reranked]
        rerank_scores = [ch["rerank_score"] for ch in reranked]

    # ── Output ────────────────────────────────────────────────────────────────
    if args.json:
        output = []
        for i, (d, m, dist) in enumerate(zip(docs, metadatas, distances)):
            item = {
                "doc_id":  m.get("doc_id"),
                "page":    m.get("page"),
                "score":   round(1 - dist, 4),
                "tags":    m.get("tags", "").split(","),
                "text":    d,
                "source":  m.get("source", ""),
            }
            if rerank_scores:
                item["rerank_score"] = round(rerank_scores[i], 4)
            output.append(item)
        print(json.dumps(output, ensure_ascii=False, indent=2))
    else:
        print(f"\n🔍 Búsqueda: \"{args.ask}\"")
        print(f"   Proyecto: {project_norm}  |  Colección: {collection_name}  |  Top: {args.top}")
        if tag_list:
            print(f"   Filtro tags: {tag_list}")
        if not args.no_rerank:
            print(f"   Reranking: ✅ activo")
        print(f"   Total en colección: {collection.count()} chunks\n")

        if not docs:
            print("⚠️  Sin resultados para esta consulta.")
        else:
            for i, (d, m, dist) in enumerate(zip(docs, metadatas, distances), 1):
                rr_score = rerank_scores[i-1] if rerank_scores else None
                print(fmt_result(i, d, m, dist, rr_score))


if __name__ == "__main__":
    main()
