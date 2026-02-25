"""
embed_chunks.py
Lee chunks desde un JSONL de proyecto, genera embeddings con sentence-transformers
y los almacena en ChromaDB (persistente en data/chroma/).

Uso:
    python scripts/embed_chunks.py --chunks data/ot-1844_chunks.jsonl --project OT-1844
    python scripts/embed_chunks.py --chunks data/ot-1844_chunks.jsonl --project OT-1844 --reset
"""

import argparse
import hashlib
import json
import sys
from pathlib import Path

# utilidades compartidas
sys.path.insert(0, str(Path(__file__).parent))
from rag_utils import normalize_project_code, collection_name_from_project

CHROMA_DIR = Path("data/chroma")
MODEL_NAME = "paraphrase-multilingual-mpnet-base-v2"
BATCH_SIZE = 64


def load_chunks(path: str):
    chunks = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                chunks.append(json.loads(line))
    return chunks


def make_doc_id(chunk: dict, idx: int) -> str:
    """ID único por chunk: proyecto-docid-pag-chunk-sourcehash.

    Incluye hash corto de source_path para evitar colisiones cuando distintos
    PDFs comparten doc_id (p. ej. revisiones/duplicados con mismo nombre base).
    """
    proj = chunk.get("project", "UNK")
    doc  = chunk.get("doc_id", "UNK")
    pg   = chunk.get("page", 0)
    ck   = chunk.get("chunk", idx)
    src  = chunk.get("source_path", "")
    src_hash = hashlib.sha1(src.encode("utf-8", errors="ignore")).hexdigest()[:10] if src else "nosrc"
    return f"{proj}_{doc}_p{pg}_c{ck}_{src_hash}"


def main():
    ap = argparse.ArgumentParser(description="Genera embeddings de chunks y los carga en ChromaDB")
    ap.add_argument("--chunks",   required=True, help="Ruta al archivo JSONL de chunks")
    ap.add_argument("--project",  required=True, help="Código de proyecto (ej. OT-1844)")
    ap.add_argument("--reset",    action="store_true", help="Borra la colección antes de insertar")
    ap.add_argument("--batch",    type=int, default=BATCH_SIZE, help="Tamaño de batch para embeddings")
    ap.add_argument("--model",    default=MODEL_NAME, help="Modelo sentence-transformers a usar")
    ap.add_argument("--chroma-dir", default=str(CHROMA_DIR), help="Directorio de ChromaDB")
    args = ap.parse_args()

    # ── Imports con feedback temprano ────────────────────────────────────────
    print("→ Cargando dependencias...")
    try:
        import chromadb
        from sentence_transformers import SentenceTransformer
    except ImportError as e:
        print(f"❌ Dependencia faltante: {e}")
        print("   Ejecuta: pip install sentence-transformers chromadb")
        sys.exit(1)

    # ── Cargar chunks ────────────────────────────────────────────────────────
    print(f"→ Leyendo chunks desde {args.chunks}...")
    chunks = load_chunks(args.chunks)
    if not chunks:
        print("❌ No se encontraron chunks.")
        sys.exit(1)
    print(f"   {len(chunks)} chunks cargados.")

    # ── Modelo de embeddings ─────────────────────────────────────────────────
    print(f"→ Cargando modelo '{args.model}' (puede tardar en primer uso)...")
    model = SentenceTransformer(args.model)

    # ── ChromaDB ─────────────────────────────────────────────────────────────
    chroma_path = Path(args.chroma_dir)
    chroma_path.mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(path=str(chroma_path))

    project_norm = normalize_project_code(args.project)
    collection_name = collection_name_from_project(project_norm)
    if args.reset:
        try:
            client.delete_collection(collection_name)
            print(f"   Colección '{collection_name}' eliminada (reset).")
        except Exception:
            pass

    collection = client.get_or_create_collection(
        name=collection_name,
        metadata={"hnsw:space": "cosine"},
    )

    existing = set(collection.get(include=[])["ids"])
    print(f"   Colección '{collection_name}': {len(existing)} docs existentes.")

    # ── Filtrar ya cargados ───────────────────────────────────────────────────
    new_chunks = []
    for i, ch in enumerate(chunks):
        did = make_doc_id(ch, i)
        if did not in existing:
            new_chunks.append((did, ch))

    if not new_chunks:
        print("✅ Todos los chunks ya están en ChromaDB. Nada que hacer.")
        return

    print(f"→ {len(new_chunks)} chunks nuevos a procesar (batch={args.batch})...")

    # ── Embeddings en batches ─────────────────────────────────────────────────
    total = len(new_chunks)
    inserted = 0

    for start in range(0, total, args.batch):
        batch = new_chunks[start : start + args.batch]
        ids       = [b[0] for b in batch]
        texts     = [b[1].get("text", "") for b in batch]
        metadatas = []
        for _, ch in batch:
            meta = {
                "project":  ch.get("project", ""),
                "doc_id":   ch.get("doc_id", ""),
                "page":     str(ch.get("page", "")),
                "chunk":    str(ch.get("chunk", "")),
                "tags":     ",".join(ch.get("tags", [])),
                "source":   ch.get("source_path", ""),
            }
            metadatas.append(meta)

        embeddings = model.encode(texts, show_progress_bar=False).tolist()

        collection.add(
            ids=ids,
            documents=texts,
            embeddings=embeddings,
            metadatas=metadatas,
        )
        inserted += len(batch)
        pct = inserted / total * 100
        print(f"   [{pct:5.1f}%] {inserted}/{total} chunks insertados", end="\r")

    print(f"\n✅ Listo. {inserted} chunks nuevos en ChromaDB.")
    print(f"   Proyecto normalizado: '{project_norm}'")
    print(f"   Colección: '{collection_name}'")
    print(f"   Total en colección: {collection.count()}")
    print(f"   Directorio: {chroma_path.resolve()}")


if __name__ == "__main__":
    main()
