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
import time
from pathlib import Path

CHROMA_DIR   = Path("data/chroma")
MODEL_NAME   = "paraphrase-multilingual-mpnet-base-v2"
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
    ap.add_argument("--top",        type=int, default=None, help="Número de resultados")
    ap.add_argument("--tags",       default="", help="Filtrar por tags (csv), ej: pintura,coating")
    ap.add_argument("--doc",        default="", help="Filtrar por doc_id (substring)")
    ap.add_argument("--json",       action="store_true", help="Output en JSON")
    ap.add_argument("--no-rerank",  action="store_true", help="Desactivar reranking (solo embeddings)")
    ap.add_argument("--model",      default=MODEL_NAME)
    ap.add_argument("--reranker-model", default=None, help="Modelo CrossEncoder para reranking")
    ap.add_argument("--hybrid", dest="hybrid", action="store_true", help="Activa búsqueda híbrida (vector + BM25)")
    ap.add_argument("--no-hybrid", dest="hybrid", action="store_false", help="Solo vector")
    ap.set_defaults(hybrid=True)
    ap.add_argument("--recall-k", type=int, default=50, help="Candidatos previos para fusión/reranking")
    ap.add_argument("--rrf-k", type=int, default=60, help="Constante k para fusión RRF")
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
    from rag_utils import (
        get_reranker_model,
        rerank_chunks,
        normalize_project_code,
        collection_name_from_project,
        RERANK_MODEL_NAME,
        DEFAULT_TOP_K,
        bm25_rank,
        rrf_fuse,
        get_or_build_bm25_index,
        bm25_rank_from_index,
    )
    from rag_metrics import (
        RagQueryLog,
        write_rag_log,
        count_tokens_cl100k,
        now_utc_iso,
        ms_since,
    )

    if args.top is None:
        args.top = DEFAULT_TOP_K
    if not args.reranker_model:
        args.reranker_model = RERANK_MODEL_NAME

    t0 = time.perf_counter()

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
        conditions = [{"tags": {"$contains": t}} for t in tag_list]
        where = {"$or": conditions} if len(conditions) > 1 else conditions[0]

    # ── Recuperación vectorial inicial (recall) ──────────────────────────────
    recall_k = min(max(args.top, args.recall_k), collection.count())
    query_kwargs = dict(
        query_embeddings=q_embedding,
        n_results=recall_k,
        include=["documents", "metadatas", "distances"],
    )
    if where:
        query_kwargs["where"] = where

    results = collection.query(**query_kwargs)
    v_docs = results["documents"][0]
    v_metas = results["metadatas"][0]
    v_dists = results["distances"][0]

    # ── Recuperación léxica BM25 (opcional híbrida) ──────────────────────────
    lex_candidates = []
    if args.hybrid:
        get_kwargs = {"include": ["documents", "metadatas"]}
        if where:
            get_kwargs["where"] = where
        all_rows = collection.get(**get_kwargs)
        l_docs = all_rows.get("documents", [])
        l_metas = all_rows.get("metadatas", [])
        bm25_index = get_or_build_bm25_index(collection_name, l_docs)
        ranked_bm25 = bm25_rank_from_index(args.ask, bm25_index)
        for idx, bm25_s in ranked_bm25[:recall_k]:
            lex_candidates.append((l_docs[idx], l_metas[idx], bm25_s))

    # ── Fusión RRF vector + léxico ────────────────────────────────────────────
    candidates = {}
    vector_rank = []
    lexical_rank = []

    for i, (d, m, dist) in enumerate(zip(v_docs, v_metas, v_dists), start=1):
        key = f"{m.get('doc_id','')}|{m.get('page','')}|{hash(d)}"
        candidates[key] = {
            "text": d,
            "meta": m,
            "distance": dist,
            "vector_score": 1 - dist,
            "bm25_score": 0.0,
        }
        vector_rank.append(key)

    for d, m, bm25_s in lex_candidates:
        key = f"{m.get('doc_id','')}|{m.get('page','')}|{hash(d)}"
        if key not in candidates:
            candidates[key] = {
                "text": d,
                "meta": m,
                "distance": 1.0,
                "vector_score": 0.0,
                "bm25_score": bm25_s,
            }
        else:
            candidates[key]["bm25_score"] = bm25_s
        lexical_rank.append(key)

    if args.hybrid and lexical_rank:
        fused = rrf_fuse([vector_rank, lexical_rank], k=args.rrf_k)
        ordered_keys = [k for k, _ in fused][:recall_k]
    else:
        ordered_keys = vector_rank[:recall_k]

    # ── Prefiltro por doc_id ANTES de rerank final ───────────────────────────
    if args.doc:
        ordered_keys = [
            k for k in ordered_keys
            if args.doc.lower() in candidates[k]["meta"].get("doc_id", "").lower()
        ]

    # preparar listas para rerank/final
    docs = [candidates[k]["text"] for k in ordered_keys]
    metadatas = [candidates[k]["meta"] for k in ordered_keys]
    distances = [candidates[k]["distance"] for k in ordered_keys]

    # ── Reranking (si no está desactivado) ────────────────────────────────────
    rerank_scores = None
    if not args.no_rerank and docs:
        reranker = get_reranker_model(args.reranker_model)
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

    # recorte final top-k
    docs = list(docs)[:args.top]
    metadatas = list(metadatas)[:args.top]
    distances = list(distances)[:args.top]
    if rerank_scores:
        rerank_scores = list(rerank_scores)[:args.top]

    chunks_payload = []
    for i, (d, m, dist) in enumerate(zip(docs, metadatas, distances), 1):
        item = {
            "rank": i,
            "doc_id": m.get("doc_id"),
            "page": m.get("page"),
            "score": round(1 - dist, 6),
            "distance": round(float(dist), 6),
        }
        if rerank_scores:
            item["rerank_score"] = round(float(rerank_scores[i - 1]), 6)
        chunks_payload.append(item)

    write_rag_log(
        RagQueryLog(
            ts_utc=now_utc_iso(),
            source="search_project",
            project=project_norm,
            collection=collection_name,
            query=args.ask,
            tokens_sent=count_tokens_cl100k(args.ask),
            chunks_retrieved=chunks_payload,
            top_k_requested=args.top,
            top_k_returned=len(chunks_payload),
            retrieval_mode="hybrid" if args.hybrid else "vector",
            rerank_enabled=not args.no_rerank,
            elapsed_ms=ms_since(t0),
            extra={"recall_k": recall_k, "rrf_k": args.rrf_k},
        )
    )

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
        print(f"   Retrieval: {'híbrido (vector+BM25)' if args.hybrid else 'vector'}")
        if not args.no_rerank:
            print(f"   Reranking: ✅ activo ({args.reranker_model})")
        print(f"   Total en colección: {collection.count()} chunks\n")

        if not docs:
            print("⚠️  Sin resultados para esta consulta.")
        else:
            for i, (d, m, dist) in enumerate(zip(docs, metadatas, distances), 1):
                rr_score = rerank_scores[i-1] if rerank_scores else None
                print(fmt_result(i, d, m, dist, rr_score))


if __name__ == "__main__":
    main()
