"""
episode_writer.py
Indexa episodios de memoria general en ChromaDB colección: lilit_memory
Uso:
 python scripts/episode_writer.py --text "resumen de sesión" --tags "trading,python"
 python scripts/episode_writer.py --file memory/episodes/2026-03-06.md
"""

import argparse
import hashlib
import sys
import time
from datetime import datetime
from pathlib import Path

CHROMA_DIR = Path("data/chroma")
COLLECTION_NAME = "lilit_memory"
MODEL_NAME = "paraphrase-multilingual-mpnet-base-v2"
CHUNK_SIZE = 400
CHUNK_OVERLAP = 80


def chunk_text(text: str) -> list[str]:
 words = text.split()
 chunks = []
 i = 0
 while i < len(words):
 chunk = " ".join(words[i:i + CHUNK_SIZE])
 chunks.append(chunk)
 i += CHUNK_SIZE - CHUNK_OVERLAP
 return [c for c in chunks if len(c.strip()) > 30]


def get_collection():
 import chromadb
 from chromadb.config import Settings
 CHROMA_DIR.mkdir(parents=True, exist_ok=True)
 client = chromadb.PersistentClient(
 path=str(CHROMA_DIR),
 settings=Settings(anonymized_telemetry=False)
 )
 return client.get_or_create_collection(
 name=COLLECTION_NAME,
 metadata={"hnsw:space": "cosine"}
 )


def embed(texts: list[str]):
 from sentence_transformers import SentenceTransformer
 model = SentenceTransformer(MODEL_NAME)
 return model.encode(texts, show_progress_bar=False).tolist()


def index_episode(text: str, tags: str = "", source: str = "session"):
 chunks = chunk_text(text)
 if not chunks:
 print("Sin contenido para indexar.")
 return

 collection = get_collection()
 embeddings = embed(chunks)
 date_str = datetime.now().strftime("%Y-%m-%d %H:%M")

 ids = []
 docs = []
 metas = []
 embeds = []

 for i, (chunk, emb) in enumerate(zip(chunks, embeddings)):
 chunk_id = hashlib.md5(f"{source}_{i}_{chunk[:50]}".encode()).hexdigest()[:16]
 # saltar si ya existe
 existing = collection.get(ids=[chunk_id])
 if existing["ids"]:
 continue
 ids.append(chunk_id)
 docs.append(chunk)
 metas.append({
 "source": source,
 "date": date_str,
 "tags": tags,
 "chunk_index": i
 })
 embeds.append(emb)

 if not ids:
 print(f"Todos los chunks ya estaban indexados ({len(chunks)} chunks).")
 return

 collection.add(ids=ids, documents=docs, metadatas=metas, embeddings=embeds)
 print(f"Indexados {len(ids)} chunks nuevos en '{COLLECTION_NAME}' | source: {source}")


def main():
 parser = argparse.ArgumentParser()
 parser.add_argument("--text", type=str, help="Texto directo a indexar")
 parser.add_argument("--file", type=str, help="Ruta a archivo .md a indexar")
 parser.add_argument("--tags", type=str, default="", help="Tags separados por coma")
 parser.add_argument("--source", type=str, default="session", help="Nombre de fuente")
 args = parser.parse_args()

 if args.file:
 path = Path(args.file)
 if not path.exists():
 print(f"Archivo no encontrado: {path}")
 sys.exit(1)
 text = path.read_text(encoding="utf-8")
 source = path.stem
 elif args.text:
 text = args.text
 source = args.source
 else:
 print("Usa --text o --file")
 sys.exit(1)

 index_episode(text=text, tags=args.tags, source=source)


if __name__ == "__main__":
 main()