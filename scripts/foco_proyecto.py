"""
foco_proyecto.py
Interfaz de alto nivel para focos de proyecto.
Combina búsqueda semántica (ChromaDB) con síntesis vía OpenClaw (webhook + WS polling).

Uso interactivo:
    python scripts/foco_proyecto.py --project OT-1844

Consulta directa:
    python scripts/foco_proyecto.py --project OT-1844 --ask "¿cuál es el DFT total del esquema de pintura?"
    python scripts/foco_proyecto.py --project OT-1844 --ask "filete mínimo en terreno" --top 8

Modo debug (ver chunks sin síntesis):
    python scripts/foco_proyecto.py --project OT-1844 --ask "..." --no-synth

Variables de entorno requeridas:
    OPENCLAW_HOOK_TOKEN     Token del bloque hooks en openclaw.json
    OPENCLAW_GATEWAY_TOKEN  Token del bloque gateway.auth en openclaw.json

Variables opcionales:
    OPENCLAW_HTTP_URL       (default: http://127.0.0.1:18789)
    OPENCLAW_WS_URL         (default: ws://127.0.0.1:18789/ws)
    OPENCLAW_HOOK_SESSION_KEY (default: hook:rag:foco)
"""

import argparse
import asyncio
import base64
import hashlib
import json
import os
import re
import sys
import textwrap
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# ── Configuración ─────────────────────────────────────────────────────────────
CHROMA_DIR        = Path("data/chroma")
MODEL_NAME        = "paraphrase-multilingual-mpnet-base-v2"
DEFAULT_TOP       = 6
MAX_CONTEXT_CHARS = 6000
RERANK_MODEL_NAME = "cross-encoder/ms-marco-MiniLM-L-6-v2"

# Caché en memoria (válido dentro del mismo proceso Python)
_EMBED_MODEL_CACHE: Dict[str, Any] = {}
_RERANK_MODEL_CACHE: Dict[str, Any] = {}

GATEWAY_HTTP  = os.getenv("OPENCLAW_HTTP_URL",          "http://127.0.0.1:18789")
GATEWAY_WS    = os.getenv("OPENCLAW_WS_URL",            "ws://127.0.0.1:18789/ws")
HOOK_TOKEN    = os.getenv("OPENCLAW_HOOK_TOKEN",        "rag-hook-edgardo-2026")
SESSION_KEY   = os.getenv("OPENCLAW_HOOK_SESSION_KEY",  "hook:rag:foco")
WAIT_TIMEOUT  = int(os.getenv("OPENCLAW_WAIT_TIMEOUT_SECONDS", "120"))
POLL_INTERVAL = float(os.getenv("OPENCLAW_POLL_INTERVAL_SECONDS", "1.5"))

OPENCLAW_CONFIG_PATH = Path(os.getenv("OPENCLAW_CONFIG_PATH", str(Path.home() / ".openclaw" / "openclaw.json")))
IDENTITY_PATH = Path.home() / ".openclaw" / "identity" / "device.json"

SYSTEM_PROMPT = """Eres un asistente técnico especializado en proyectos de fabricación estructural metálica.
Responde en español, de forma directa y técnica.
Usa SOLO la información de los fragmentos de documentos proporcionados (contexto).
Si la información no está en el contexto, dilo explícitamente.
Cita el documento de origen cuando sea relevante (formato: [DOC_ID pág. N])."""


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("ascii").rstrip("=")


def _b64url_decode(data: str) -> bytes:
    pad = "=" * ((4 - len(data) % 4) % 4)
    return base64.urlsafe_b64decode(data + pad)


def load_gateway_token_from_config() -> str:
    env_token = os.getenv("OPENCLAW_GATEWAY_TOKEN", "").strip()
    if env_token:
        return env_token
    try:
        cfg = json.loads(OPENCLAW_CONFIG_PATH.read_text(encoding="utf-8-sig"))
        token = str(cfg.get("gateway", {}).get("auth", {}).get("token", "")).strip()
        return token
    except Exception:
        return ""


def ensure_device_identity(path: Path) -> Dict[str, str]:
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import ed25519

    if path.exists():
        raw = json.loads(path.read_text(encoding="utf-8"))
        if all(k in raw for k in ("deviceId", "publicKeyPem", "privateKeyPem")):
            return {
                "deviceId": raw["deviceId"],
                "publicKeyPem": raw["publicKeyPem"],
                "privateKeyPem": raw["privateKeyPem"],
            }

    private_key = ed25519.Ed25519PrivateKey.generate()
    public_key = private_key.public_key()

    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode("utf-8")

    public_pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode("utf-8")

    public_der = public_key.public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    device_id = hashlib.sha256(public_der).hexdigest()

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "version": 1,
                "deviceId": device_id,
                "publicKeyPem": public_pem,
                "privateKeyPem": private_pem,
                "createdAtMs": int(time.time() * 1000),
            },
            ensure_ascii=False,
            indent=2,
        ) + "\n",
        encoding="utf-8",
    )

    return {"deviceId": device_id, "publicKeyPem": public_pem, "privateKeyPem": private_pem}


def build_ws_device_block(nonce: str, gateway_token: str, scopes: List[str]) -> Dict[str, Any]:
    from cryptography.hazmat.primitives import serialization

    identity = ensure_device_identity(IDENTITY_PATH)
    signed_at_ms = int(time.time() * 1000)

    private_key = serialization.load_pem_private_key(identity["privateKeyPem"].encode("utf-8"), password=None)
    public_key = serialization.load_pem_public_key(identity["publicKeyPem"].encode("utf-8"))

    public_raw = public_key.public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )

    payload = "|".join([
        "v2",
        identity["deviceId"],
        "cli",
        "cli",
        "operator",
        ",".join(scopes),
        str(signed_at_ms),
        gateway_token or "",
        nonce,
    ])

    signature = private_key.sign(payload.encode("utf-8"))

    return {
        "id": identity["deviceId"],
        "publicKey": _b64url_encode(public_raw),
        "signature": _b64url_encode(signature),
        "signedAt": signed_at_ms,
        "nonce": nonce,
    }


# ── ChromaDB ──────────────────────────────────────────────────────────────────

def load_chroma(chroma_dir: str, project: str):
    import chromadb
    client = chromadb.PersistentClient(path=chroma_dir)
    collection_name = project.lower().replace("-", "_")
    try:
        return client.get_collection(collection_name)
    except Exception:
        print(f"❌ Colección '{collection_name}' no existe.")
        print(f"   Ejecuta primero: python scripts/embed_chunks.py --chunks data/{project.lower().replace('-','_')}_chunks.jsonl --project {project}")
        sys.exit(1)


# ── Búsqueda semántica ────────────────────────────────────────────────────────

def semantic_search(collection, model, query: str, top: int) -> list:
    q_emb = model.encode([query]).tolist()
    results = collection.query(
        query_embeddings=q_emb,
        n_results=min(top, collection.count()),
        include=["documents", "metadatas", "distances"],
    )
    out = []
    for doc, meta, dist in zip(
        results["documents"][0],
        results["metadatas"][0],
        results["distances"][0],
    ):
        out.append({
            "text":   doc,
            "doc_id": meta.get("doc_id", ""),
            "page":   meta.get("page", ""),
            "tags":   meta.get("tags", "").split(","),
            "score":  round(1 - dist, 4),
        })
    return out


def rerank_chunks(query: str, chunks: List[Dict[str, Any]], reranker) -> List[Dict[str, Any]]:
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


def build_context(chunks: list, max_chars: int) -> str:
    parts = []
    total = 0
    for ch in chunks:
        if "rerank_score" in ch:
            header = f"[{ch['doc_id']} pág. {ch['page']} | sim {ch['score']} | rerank {ch['rerank_score']:.4f}]\n"
        else:
            header = f"[{ch['doc_id']} pág. {ch['page']} | score {ch['score']}]\n"
        block  = header + ch["text"] + "\n"
        if total + len(block) > max_chars:
            remaining = max_chars - total
            if remaining > 100:
                parts.append(block[:remaining] + "…")
            break
        parts.append(block)
        total += len(block)
    return "\n---\n".join(parts)


# ── OpenClaw: hook + WS polling ───────────────────────────────────────────────

def fire_hook(message: str) -> Tuple[float, Dict[str, Any]]:
    import urllib.request, urllib.error
    url = f"{GATEWAY_HTTP.rstrip('/')}/hooks/agent"
    payload = json.dumps({
        "message":    message,
        "sessionKey": SESSION_KEY,
        "wakeMode":   "now",
        "deliver":    False,
    }).encode("utf-8")
    req = urllib.request.Request(
        url, data=payload,
        headers={
            "Authorization": f"Bearer {HOOK_TOKEN}",
            "Content-Type":  "application/json",
        },
        method="POST"
    )
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=20) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    if not data.get("ok"):
        raise RuntimeError(f"/hooks/agent error: {data}")
    return t0, data


async def ws_request(ws, method: str, params: Dict[str, Any], timeout: float = 15.0) -> Dict[str, Any]:
    req_id = str(uuid.uuid4())
    await ws.send(json.dumps({"type": "req", "id": req_id, "method": method, "params": params}))
    deadline = time.time() + timeout
    while time.time() < deadline:
        raw = await asyncio.wait_for(ws.recv(), timeout=max(0.1, deadline - time.time()))
        msg = json.loads(raw)
        if msg.get("type") == "res" and msg.get("id") == req_id:
            if not msg.get("ok", False):
                raise RuntimeError(f"WS {method} error: {msg.get('error')}")
            return msg.get("payload", {})
    raise TimeoutError(f"Timeout WS method={method}")


def extract_text_from_content(content: Any) -> str:
    if content is None:
        return ""
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict):
                txt = item.get("text")
                if isinstance(txt, str):
                    parts.append(txt)
        return "\n".join(p for p in parts if p).strip()
    if isinstance(content, dict):
        txt = content.get("text")
        if isinstance(txt, str):
            return txt.strip()
    return ""


def message_timestamp(msg: Dict[str, Any]) -> Optional[float]:
    for key in ("timestampMs", "createdAtMs", "tsMs"):
        v = msg.get(key)
        if isinstance(v, (int, float)):
            return float(v) / 1000.0
    for key in ("timestamp", "createdAt", "time"):
        v = msg.get(key)
        if isinstance(v, (int, float)):
            return float(v / 1000.0) if v > 10_000_000_000 else float(v)
    return None


def pick_latest_assistant_reply(messages: List[Dict[str, Any]], t0: float) -> Optional[str]:
    for msg in reversed(messages):
        if str(msg.get("role", "")).lower() != "assistant":
            continue
        ts = message_timestamp(msg)
        if ts is not None and ts < t0:
            continue
        text = extract_text_from_content(msg.get("content"))
        if not text:
            text = str(msg.get("text", "")).strip()
        if text:
            return text
    return None


async def connect_and_wait_reply(t0: float) -> str:
    try:
        import websockets
    except ImportError:
        raise RuntimeError("Instala websockets: pip install websockets")

    gateway_token = load_gateway_token_from_config()
    if not gateway_token:
        raise RuntimeError(f"No se pudo resolver OPENCLAW_GATEWAY_TOKEN ni gateway.auth.token en {OPENCLAW_CONFIG_PATH}")

    scopes = ["operator.read", "operator.write"]

    async with websockets.connect(GATEWAY_WS, max_size=8 * 1024 * 1024) as ws:
        # 1) challenge inicial
        first = json.loads(await asyncio.wait_for(ws.recv(), timeout=10))
        if not (first.get("type") == "event" and first.get("event") == "connect.challenge"):
            raise RuntimeError(f"Frame inesperado en connect: {first}")

        nonce = str(first.get("payload", {}).get("nonce", "")).strip()
        if not nonce:
            raise RuntimeError("No llegó nonce en connect.challenge")

        device_block = build_ws_device_block(nonce=nonce, gateway_token=gateway_token, scopes=scopes)

        # 2) autenticarse
        await ws_request(ws, "connect", {
            "minProtocol": 3,
            "maxProtocol": 3,
            "client": {"id": "cli", "version": "0.1.0", "platform": "python", "mode": "cli"},
            "role": "operator",
            "scopes": scopes,
            "auth": {"token": gateway_token},
            "device": device_block,
        }, timeout=10)

        # 3) polling
        deadline = time.time() + WAIT_TIMEOUT
        while time.time() < deadline:
            hist = await ws_request(ws, "chat.history", {"sessionKey": SESSION_KEY, "limit": 200}, timeout=15)
            messages = hist.get("messages", [])
            if isinstance(messages, list):
                answer = pick_latest_assistant_reply(messages, t0)
                if answer:
                    return answer
            await asyncio.sleep(POLL_INTERVAL)
            print(".", end="", flush=True)

    raise TimeoutError(f"Sin respuesta del assistant en {WAIT_TIMEOUT}s")


def synthesize_openclaw(query: str, context: str) -> str:
    full_message = f"{SYSTEM_PROMPT}\n\nContexto de documentos:\n{context}\n\nPregunta: {query}"
    try:
        t0, ack = fire_hook(full_message)
        print(f"   ⏳ Procesando (runId: {ack.get('runId','?')[:8]}…)", end="", flush=True)
        result = asyncio.run(connect_and_wait_reply(t0))
        print(" ✅")
        return result
    except RuntimeError as e:
        return f"[❌ {e}]"
    except TimeoutError as e:
        print(" ⏱️")
        return f"[❌ {e}]"
    except Exception as e:
        return f"[❌ Error inesperado: {e}]"


# ── Síntesis local (fallback) ─────────────────────────────────────────────────

def synthesize_local(query: str, context: str) -> str:
    sentences = re.split(r"(?<=[.!?])\s+", context)
    q_words = set(re.findall(r"\w+", query.lower()))
    scored = []
    for s in sentences:
        s_words = set(re.findall(r"\w+", s.lower()))
        overlap = len(q_words & s_words)
        if overlap > 0 and len(s) > 30:
            scored.append((overlap, s))
    scored.sort(key=lambda x: -x[0])
    top_sentences = [s for _, s in scored[:6]]
    return " ".join(top_sentences) if top_sentences else "No se encontraron fragmentos relevantes."


# ── Flujo principal ───────────────────────────────────────────────────────────

def get_embedding_model(model_name: str):
    if model_name in _EMBED_MODEL_CACHE:
        return _EMBED_MODEL_CACHE[model_name]
    from sentence_transformers import SentenceTransformer
    model = SentenceTransformer(model_name)
    _EMBED_MODEL_CACHE[model_name] = model
    return model


def get_reranker_model(model_name: str):
    if model_name in _RERANK_MODEL_CACHE:
        return _RERANK_MODEL_CACHE[model_name]
    from sentence_transformers import CrossEncoder
    model = CrossEncoder(model_name)
    _RERANK_MODEL_CACHE[model_name] = model
    return model


def answer(query: str, collection, emb_model, reranker, top: int, no_synth: bool, use_local: bool):
    print(f"\n🔍 Buscando: \"{query}\"\n")
    chunks = semantic_search(collection, emb_model, query, top)

    if not chunks:
        print("⚠️  Sin resultados.")
        return

    chunks = rerank_chunks(query, chunks, reranker)

    if not chunks:
        print("⚠️  Sin resultados.")
        return

    print(f"📄 Fuentes relevantes (rerankeadas) ({len(chunks)}):")
    for i, ch in enumerate(chunks, 1):
        rr = ch.get("rerank_score")
        rr_txt = f"  rerank={rr:.4f}" if isinstance(rr, (int, float)) else ""
        print(f"   [{i}] {ch['doc_id']}  pág.{ch['page']}  score={ch['score']}{rr_txt}  tags={','.join(ch['tags'][:3])}")

    if no_synth:
        print("\n── Chunks (modo debug) ──")
        for i, ch in enumerate(chunks, 1):
            preview = ch["text"][:500].replace("\n", " ")
            print(f"\n[{i}] {ch['doc_id']} p.{ch['page']}\n{preview}")
        return

    context = build_context(chunks, MAX_CONTEXT_CHARS)
    print("\n💬 Respuesta:\n" + "─" * 60)

    if use_local:
        print("   (modo local — sin LLM)")
        resp = synthesize_local(query, context)
    else:
        print(f"   (vía OpenClaw → {GATEWAY_HTTP})")
        resp = synthesize_openclaw(query, context)

    for line in resp.split("\n"):
        print(textwrap.fill(line, width=90) if len(line) > 90 else line)
    print("─" * 60)


def main():
    ap = argparse.ArgumentParser(description="Foco de proyecto — RAG semántico con OpenClaw")
    ap.add_argument("--project",    required=True)
    ap.add_argument("--ask",        default="")
    ap.add_argument("--top",        type=int, default=DEFAULT_TOP)
    ap.add_argument("--no-synth",   action="store_true")
    ap.add_argument("--local",      action="store_true")
    ap.add_argument("--model",      default=MODEL_NAME)
    ap.add_argument("--chroma-dir", default=str(CHROMA_DIR))
    args = ap.parse_args()

    try:
        import sentence_transformers  # noqa: F401
    except ImportError:
        print("❌ Ejecuta: pip install sentence-transformers chromadb")
        sys.exit(1)

    print(f"→ Proyecto:   {args.project}")
    print(f"→ OpenClaw:   {GATEWAY_HTTP}  |  WS: {GATEWAY_WS}")
    print(f"→ Sesión:     {SESSION_KEY}")
    t0 = time.perf_counter()
    emb_model = get_embedding_model(args.model)
    t1 = time.perf_counter()
    reranker = get_reranker_model(RERANK_MODEL_NAME)
    t2 = time.perf_counter()
    print(f"→ Embeddings ({args.model}) listo en {(t1 - t0):.2f}s")
    print(f"→ Reranker ({RERANK_MODEL_NAME}) listo en {(t2 - t1):.2f}s")

    collection = load_chroma(args.chroma_dir, args.project)
    total = collection.count()
    print(f"→ Colección lista: {total} chunks indexados\n")

    if args.ask:
        answer(args.ask, collection, emb_model, reranker, args.top, args.no_synth, args.local)
    else:
        print(f"✅ Foco activo: {args.project} ({total} chunks)")
        print("   Escribe tu consulta o 'salir' para terminar.\n")
        while True:
            try:
                query = input("❓ ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\n👋 Saliendo.")
                break
            if not query:
                continue
            if query.lower() in ("salir", "exit", "quit", "q"):
                print("👋 Saliendo.")
                break
            answer(query, collection, emb_model, reranker, args.top, args.no_synth, args.local)


if __name__ == "__main__":
    main()
