"""
memory_search.py
Busqueda semantica sobre memoria general de Lilit en ChromaDB coleccion: lilit_memory
Uso:
 python scripts/memory_search.py --ask "como hicimos el script del advance"
 python scripts/memory_search.py --ask "configuracion RAG" --top 3
"""

import argparse
import sys
from pathlib import Path

CHROMA_DIR = Path("data/chroma")
COLLECTION_NAME = "lilit_memory"
MODEL_NAME = "paraphrase-multilingual-mpnet-base-v2"
RERANK_MODEL = "cross-encoder/ms-marco-MiniLM-L-6-v2"
PREVIEW_CHARS = 400


def search_memory(query: str, top: int = 3) -> list[dict]:
 import chromadb
 from chromadb.config import Settings
 from sentence_transformers import SentenceTransformer, CrossEncoder

 client = chromadb.PersistentClient(
 path=str(CHROMA_DIR),
 settings=Settings(anonymized_telemetry=False)
 )

 try:
 collection = client.get_collection(COLLECTION_NAME)
 except Exception:
 print("Coleccion lilit_memory no encontrada. Indexa episodios primero.")
 sys.exit(1)

 total = collection.count()
 if total == 0:
 print("La coleccion esta vacia.")
 sys.exit(1)

 embedder = SentenceTransformer(MODEL_NAME)
 query_emb = embedder.encode([query]).tolist()

 n_retrieve = min(top * 3, total)
 results = collection.query(
 query_embeddings=query_emb,
 n_results=n_retrieve,
 include=["documents", "metadatas", "distances"]
 )

 docs = results["documents"][0]
 metas = results["metadatas"][0]
 dists = results["distances"][0]

 if not docs:
 print("Sin resultados.")
 return []

 reranker = CrossEncoder(RERANK_MODEL)
 pairs = [[query, doc] for doc in docs]
 scores = reranker.predict(pairs)

 ranked = sorted(
 zip(docs, metas, dists, scores),
 key=lambda x: x[3],
 reverse=True
 )[:top]

 return [
 {
 "doc": doc,
 "source": meta.get("source", "?"),
 "date": meta.get("date", "?"),
 "tags": meta.get("tags", ""),
 "score": round(float(score), 4)
 }
 for doc, meta, dist, score in ranked
 ]


def main():
 parser = argparse.ArgumentParser()
 parser.add_argument("--ask", type=str, required=True, help="Query de busqueda")
 parser.add_argument("--top", type=int, default=3, help="Resultados a retornar")
 args = parser.parse_args()

 print(f"Buscando en memoria general: '{args.ask}'")
 print(f"Coleccion: {COLLECTION_NAME} | Top: {args.top}")
 print("-" * 60)

 results = search_memory(query=args.ask, top=args.top)

 if not results:
 print("No se encontraron resultados relevantes.")
 return

 for i, r in enumerate(results, 1):
 preview = r["doc"][:PREVIEW_CHARS]
 if len(r["doc"]) > PREVIEW_CHARS:
 preview += "..."
 print(f"[{i}] source: {r['source']} | fecha: {r['date']} | rerank: {r['score']}")
 print(f" tags: {r['tags']}")
 print(f" {preview}")
 print()


if __name__ == "__main__":
 main()