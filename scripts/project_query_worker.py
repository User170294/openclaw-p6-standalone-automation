"""
project_query_worker.py
Worker persistente para consultas RAG por socket TCP loopback.

Protocolo por conexión:
  - Cliente envía 1 línea JSON (request)
  - Worker responde 1 línea JSON (response)
  - Se cierra conexión

Request:
  {"request_id":"uuid","project":"OT-1844","ask":"query","top":10,"hybrid":true,"rerank":true}

Response:
  {"request_id":"uuid","chunks":[...],"tokens_sent":N,"elapsed_ms":N,"error":null}
"""

import argparse
import atexit
import json
import os
import signal
import socket
import subprocess
import sys
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

import chromadb
from sentence_transformers import SentenceTransformer

sys.path.insert(0, str(Path(__file__).parent))
from rag_utils import (
    get_reranker_model,
    rerank_chunks,
    normalize_project_code,
    collection_name_from_project,
    RERANK_MODEL_NAME,
    DEFAULT_TOP_K,
    rrf_fuse,
    get_or_build_bm25_index,
    bm25_rank_from_index,
    docs_md5_signature,
)
from rag_metrics import (
    RagQueryLog,
    write_rag_log,
    count_tokens_cl100k,
    now_utc_iso,
    ms_since,
)

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 18790
DEFAULT_RECALL_K = 50
DEFAULT_RRF_K = 60

PID_JSON_PATH = Path("data/worker.pid.json")


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class WorkerState:
    def __init__(
        self,
        host: str,
        port: int,
        chroma_dir: str,
        model_name: str,
        reranker_model: str,
    ):
        self.host = host
        self.port = port
        self.chroma_dir = chroma_dir
        self.model_name = model_name
        self.reranker_model = reranker_model

        self.running = True
        self.started_at = utc_now_iso()

        self.client = chromadb.PersistentClient(path=chroma_dir)
        self.embed_model = SentenceTransformer(model_name)
        self.reranker = get_reranker_model(reranker_model)

        self.collection_cache: Dict[str, Any] = {}
        self.bm25_mem_cache: Dict[str, Dict[str, Any]] = {}

        self._lock = threading.Lock()

    def get_collection(self, collection_name: str):
        if collection_name in self.collection_cache:
            return self.collection_cache[collection_name]
        col = self.client.get_collection(collection_name)
        self.collection_cache[collection_name] = col
        return col

    def get_or_refresh_mem_bm25(
        self,
        collection_name: str,
        docs: List[str],
        metas: List[dict],
    ) -> Dict[str, Any]:
        doc_count = len(docs)
        sig = docs_md5_signature(docs, sample_size=50)
        with self._lock:
            cached = self.bm25_mem_cache.get(collection_name)
            if (
                cached
                and cached.get("doc_count") == doc_count
                and cached.get("docs_sig_md5") == sig
                and "index" in cached
                and "docs" in cached
                and "metas" in cached
            ):
                return cached

            idx = get_or_build_bm25_index(collection_name, docs)
            payload = {
                "doc_count": doc_count,
                "docs_sig_md5": sig,
                "index": idx,
                "docs": docs,
                "metas": metas,
            }
            self.bm25_mem_cache[collection_name] = payload
            return payload


def write_pid_json(state: WorkerState, path: Path = PID_JSON_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "pid": os.getpid(),
        "host": state.host,
        "port": state.port,
        "started_at": state.started_at,
        "model": state.model_name,
        "chroma_dir": state.chroma_dir,
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def remove_pid_json(path: Path = PID_JSON_PATH) -> None:
    try:
        if path.exists():
            path.unlink()
    except Exception:
        pass


def is_pid_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    if os.name == "nt":
        p = subprocess.run(
            ["tasklist", "/FI", f"PID eq {pid}", "/FO", "CSV", "/NH"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        out = (p.stdout or "").strip()
        return out.startswith('"')
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def ensure_single_instance(path: Path = PID_JSON_PATH) -> None:
    if not path.exists():
        return
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
        pid = int(payload.get("pid", 0))
    except Exception:
        return
    if pid > 0 and is_pid_alive(pid):
        raise RuntimeError(f"Worker ya activo con pid={pid} (ver {path})")


def parse_request(line: str) -> Dict[str, Any]:
    obj = json.loads(line)
    if not isinstance(obj, dict):
        raise ValueError("Request debe ser objeto JSON")
    if obj.get("shutdown") is True:
        return obj
    if "request_id" not in obj or "project" not in obj or "ask" not in obj:
        raise ValueError("Request inválido: requiere request_id, project, ask")
    return obj


def chunk_key(meta: dict, text: str) -> str:
    return f"{meta.get('doc_id','')}|{meta.get('page','')}|{hash(text)}"


def run_query(state: WorkerState, req: Dict[str, Any]) -> Dict[str, Any]:
    request_id = str(req.get("request_id"))
    project = str(req.get("project", "")).strip()
    ask = str(req.get("ask", "")).strip()
    top = int(req.get("top", DEFAULT_TOP_K) or DEFAULT_TOP_K)
    hybrid = bool(req.get("hybrid", True))
    rerank = bool(req.get("rerank", True))

    if top <= 0:
        top = DEFAULT_TOP_K
    if not project:
        raise ValueError("project vacío")
    if not ask:
        raise ValueError("ask vacío")

    t0 = time.perf_counter()
    project_norm = normalize_project_code(project)
    collection_name = collection_name_from_project(project_norm)
    collection = state.get_collection(collection_name)
    total_docs = collection.count()
    if total_docs == 0:
        return {
            "request_id": request_id,
            "chunks": [],
            "tokens_sent": count_tokens_cl100k(ask),
            "elapsed_ms": ms_since(t0),
            "error": None,
        }

    q_emb = state.embed_model.encode([ask]).tolist()
    recall_k = min(max(top, DEFAULT_RECALL_K), total_docs)
    vec = collection.query(
        query_embeddings=q_emb,
        n_results=recall_k,
        include=["documents", "metadatas", "distances"],
    )

    candidates: Dict[str, Dict[str, Any]] = {}
    vector_rank: List[str] = []
    lexical_rank: List[str] = []

    v_docs = vec["documents"][0]
    v_metas = vec["metadatas"][0]
    v_dists = vec["distances"][0]
    for d, m, dist in zip(v_docs, v_metas, v_dists):
        key = chunk_key(m, d)
        candidates[key] = {
            "text": d,
            "meta": m,
            "distance": float(dist),
            "score": float(1 - dist),
            "bm25_score": 0.0,
        }
        vector_rank.append(key)

    if hybrid:
        all_rows = collection.get(include=["documents", "metadatas"])
        docs_all = all_rows.get("documents", []) or []
        metas_all = all_rows.get("metadatas", []) or []
        mem_payload = state.get_or_refresh_mem_bm25(collection_name, docs_all, metas_all)
        bm25_ranked = bm25_rank_from_index(ask, mem_payload["index"])
        for idx, score in bm25_ranked[:recall_k]:
            d = mem_payload["docs"][idx]
            m = mem_payload["metas"][idx]
            key = chunk_key(m, d)
            if key not in candidates:
                candidates[key] = {
                    "text": d,
                    "meta": m,
                    "distance": 1.0,
                    "score": 0.0,
                    "bm25_score": float(score),
                }
            else:
                candidates[key]["bm25_score"] = float(score)
            lexical_rank.append(key)

    if hybrid and lexical_rank:
        fused = rrf_fuse([vector_rank, lexical_rank], k=DEFAULT_RRF_K)
        ordered_keys = [k for k, _ in fused][:recall_k]
    else:
        ordered_keys = vector_rank[:recall_k]

    docs = [candidates[k]["text"] for k in ordered_keys]
    metas = [candidates[k]["meta"] for k in ordered_keys]
    dists = [candidates[k]["distance"] for k in ordered_keys]

    rerank_scores = None
    if rerank and docs:
        chunks_for_rerank = [
            {
                "text": d,
                "doc_id": m.get("doc_id"),
                "page": m.get("page"),
                "tags": m.get("tags", "").split(",") if isinstance(m.get("tags", ""), str) else [],
                "score": 1 - dist,
                "distance": dist,
            }
            for d, m, dist in zip(docs, metas, dists)
        ]
        reranked = rerank_chunks(ask, chunks_for_rerank, state.reranker)
        docs = [r["text"] for r in reranked]
        metas = [{"doc_id": r["doc_id"], "page": r["page"], "tags": ",".join(r.get("tags", []))} for r in reranked]
        dists = [float(r["distance"]) for r in reranked]
        rerank_scores = [float(r["rerank_score"]) for r in reranked]

    docs = docs[:top]
    metas = metas[:top]
    dists = dists[:top]
    if rerank_scores:
        rerank_scores = rerank_scores[:top]

    chunks = []
    chunks_log = []
    for i, (d, m, dist) in enumerate(zip(docs, metas, dists), start=1):
        item = {
            "rank": i,
            "doc_id": m.get("doc_id"),
            "page": m.get("page"),
            "tags": m.get("tags", "").split(",") if isinstance(m.get("tags", ""), str) else [],
            "score": round(1 - dist, 6),
            "distance": round(float(dist), 6),
            "text": d,
        }
        if rerank_scores:
            item["rerank_score"] = round(float(rerank_scores[i - 1]), 6)
        chunks.append(item)

        log_item = {
            "rank": i,
            "doc_id": item["doc_id"],
            "page": item["page"],
            "score": item["score"],
            "distance": item["distance"],
        }
        if "rerank_score" in item:
            log_item["rerank_score"] = item["rerank_score"]
        chunks_log.append(log_item)

    elapsed = ms_since(t0)
    tokens_sent = count_tokens_cl100k(ask)

    write_rag_log(
        RagQueryLog(
            ts_utc=now_utc_iso(),
            source="project_query_worker",
            project=project_norm,
            collection=collection_name,
            query=ask,
            tokens_sent=tokens_sent,
            chunks_retrieved=chunks_log,
            top_k_requested=top,
            top_k_returned=len(chunks_log),
            retrieval_mode="hybrid" if hybrid else "vector",
            rerank_enabled=rerank,
            elapsed_ms=elapsed,
            extra={"recall_k": recall_k, "rrf_k": DEFAULT_RRF_K},
        )
    )

    return {
        "request_id": request_id,
        "chunks": chunks,
        "tokens_sent": tokens_sent,
        "elapsed_ms": elapsed,
        "error": None,
    }


def handle_client(conn: socket.socket, state: WorkerState):
    with conn:
        conn.settimeout(30.0)
        try:
            data = b""
            while b"\n" not in data:
                chunk = conn.recv(4096)
                if not chunk:
                    break
                data += chunk
            line = data.decode("utf-8", errors="replace").strip()
            if not line:
                return
            req = parse_request(line)
            if req.get("shutdown") is True:
                state.running = False
                resp = {"ok": True}
            else:
                try:
                    resp = run_query(state, req)
                except Exception as e:
                    rid = req.get("request_id", "")
                    resp = {
                        "request_id": rid,
                        "chunks": [],
                        "tokens_sent": 0,
                        "elapsed_ms": 0.0,
                        "error": str(e),
                    }
        except Exception as e:
            resp = {
                "request_id": "",
                "chunks": [],
                "tokens_sent": 0,
                "elapsed_ms": 0.0,
                "error": f"protocol_error: {e}",
            }
        out = (json.dumps(resp, ensure_ascii=False) + "\n").encode("utf-8")
        conn.sendall(out)


def main():
    ap = argparse.ArgumentParser(description="Worker persistente de query RAG")
    ap.add_argument("--host", default=DEFAULT_HOST)
    ap.add_argument("--port", type=int, default=DEFAULT_PORT)
    ap.add_argument("--chroma-dir", default="data/chroma")
    ap.add_argument("--model", default="paraphrase-multilingual-mpnet-base-v2")
    ap.add_argument("--reranker-model", default=RERANK_MODEL_NAME)
    args = ap.parse_args()

    ensure_single_instance(PID_JSON_PATH)

    state = WorkerState(
        host=args.host,
        port=args.port,
        chroma_dir=args.chroma_dir,
        model_name=args.model,
        reranker_model=args.reranker_model,
    )

    def _shutdown_handler(signum, frame):
        state.running = False

    signal.signal(signal.SIGINT, _shutdown_handler)
    signal.signal(signal.SIGTERM, _shutdown_handler)
    if hasattr(signal, "SIGBREAK"):
        signal.signal(signal.SIGBREAK, _shutdown_handler)

    write_pid_json(state, PID_JSON_PATH)
    atexit.register(remove_pid_json, PID_JSON_PATH)
    print(f"✅ Worker up on {args.host}:{args.port} pid={os.getpid()}", file=sys.stderr)
    print(f"   PID file: {PID_JSON_PATH}", file=sys.stderr)

    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind((args.host, args.port))
    srv.listen(16)
    srv.settimeout(1.0)

    try:
        while state.running:
            try:
                conn, _addr = srv.accept()
            except socket.timeout:
                continue
            threading.Thread(target=handle_client, args=(conn, state), daemon=True).start()
    finally:
        try:
            srv.close()
        except Exception:
            pass
        remove_pid_json(PID_JSON_PATH)
        print("👋 Worker shutdown graceful", file=sys.stderr)


if __name__ == "__main__":
    main()
