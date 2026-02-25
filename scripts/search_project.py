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
DEFAULT_TOP  = 6
PREVIEW_CHARS = 400


def fmt_result(i: int, doc: str, meta: dict, dist: float) -> str:
    tags    = meta.get("tags", "")
    doc_id  = meta.get("doc_id", "?")
    page    = meta.get("page", "?")
    score   = 1 - dist  # cosine similarity (ChromaDB devuelve distancia)
    preview = doc[:PREVIEW_CHARS].replace("\n", " ")
    if len(doc) > PREVIEW_CHARS:
        preview += "…"
    return (
        f"\n{'─'*60}\n"
        f"[{i}] {doc_id}  |  pág. {page}  |  score: {score:.3f}\n"
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

    # ── Conexión ChromaDB ─────────────────────────────────────────────────────
    chroma_path = Path(args.chroma_dir)
    if not chroma_path.exists():
        print(f"❌ ChromaDB no encontrado en {chroma_path}. Ejecuta primero embed_chunks.py.")
        sys.exit(1)

    client = chromadb.PersistentClient(path=str(chroma_path))
    collection_name = args.project.lower().replace("-", "_")
    try:
        collection = client.get_collection(collection_name)
    except Exception:
        print(f"❌ Colección '{collection_name}' no existe. Ejecuta embed_chunks.py primero.")
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

    # ── Output ────────────────────────────────────────────────────────────────
    if args.json:
        output = []
        for d, m, dist in zip(docs, metadatas, distances):
            output.append({
                "doc_id":  m.get("doc_id"),
                "page":    m.get("page"),
                "score":   round(1 - dist, 4),
                "tags":    m.get("tags", "").split(","),
                "text":    d,
                "source":  m.get("source", ""),
            })
        print(json.dumps(output, ensure_ascii=False, indent=2))
    else:
        print(f"\n🔍 Búsqueda: \"{args.ask}\"")
        print(f"   Proyecto: {args.project}  |  Colección: {collection_name}  |  Top: {args.top}")
        if tag_list:
            print(f"   Filtro tags: {tag_list}")
        print(f"   Total en colección: {collection.count()} chunks\n")

        if not docs:
            print("⚠️  Sin resultados para esta consulta.")
        else:
            for i, (d, m, dist) in enumerate(zip(docs, metadatas, distances), 1):
                print(fmt_result(i, d, m, dist))


if __name__ == "__main__":
    main()
