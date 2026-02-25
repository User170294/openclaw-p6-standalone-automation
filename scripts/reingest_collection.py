"""
reingest_collection.py
Limpia una colección Chroma por proyecto y reingesta desde chunks JSONL.

Uso:
  python scripts/reingest_collection.py --project OT-1844 --chunks data/ot-1844_chunks.jsonl
  python scripts/reingest_collection.py --project OT-1844 --chunks data/ot-1844_chunks.jsonl --also-clear-bm25
"""

import argparse
import subprocess
import sys
from pathlib import Path

import chromadb

sys.path.insert(0, str(Path(__file__).parent))
from rag_utils import collection_name_from_project, normalize_project_code


def run(cmd: list[str]) -> None:
    p = subprocess.run(cmd, text=True)
    if p.returncode != 0:
        raise SystemExit(p.returncode)


def main():
    ap = argparse.ArgumentParser(description="Reingesta limpia por colección")
    ap.add_argument("--project", required=True, help="Código proyecto (ej. OT-1844)")
    ap.add_argument("--chunks", required=True, help="JSONL de chunks")
    ap.add_argument("--chroma-dir", default="data/chroma")
    ap.add_argument("--model", default="paraphrase-multilingual-mpnet-base-v2")
    ap.add_argument("--batch", type=int, default=64)
    ap.add_argument("--also-clear-bm25", action="store_true")
    args = ap.parse_args()

    chunks_path = Path(args.chunks)
    if not chunks_path.exists():
        print(f"❌ No existe chunks: {chunks_path}")
        raise SystemExit(1)

    project_norm = normalize_project_code(args.project)
    collection = collection_name_from_project(project_norm)
    chroma_dir = Path(args.chroma_dir)
    chroma_dir.mkdir(parents=True, exist_ok=True)

    print(f"→ Proyecto: {project_norm}")
    print(f"→ Colección: {collection}")
    print(f"→ Chroma dir: {chroma_dir}")
    print(f"→ Chunks: {chunks_path}")

    client = chromadb.PersistentClient(path=str(chroma_dir))
    try:
        client.delete_collection(collection)
        print(f"🧹 Colección eliminada: {collection}")
    except Exception:
        print(f"ℹ️ Colección no existía: {collection}")

    if args.also_clear_bm25:
        bm25_cache = Path("data/bm25_cache") / f"{collection}.bm25.json"
        if bm25_cache.exists():
            bm25_cache.unlink()
            print(f"🧹 BM25 cache eliminado: {bm25_cache}")
        else:
            print(f"ℹ️ BM25 cache no existe: {bm25_cache}")

    cmd = [
        sys.executable,
        "scripts/embed_chunks.py",
        "--chunks", str(chunks_path),
        "--project", project_norm,
        "--batch", str(args.batch),
        "--model", args.model,
        "--chroma-dir", str(chroma_dir),
    ]
    print("→ Reingestando con embed_chunks.py ...")
    run(cmd)
    print("✅ Reingesta limpia completada.")


if __name__ == "__main__":
    main()
