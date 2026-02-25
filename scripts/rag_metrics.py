import json
import time
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

LOG_DIR = Path("logs/rag_metrics")
LOG_DIR.mkdir(parents=True, exist_ok=True)

try:
    import tiktoken
    _ENC = tiktoken.get_encoding("cl100k_base")
except Exception:
    _ENC = None


def count_tokens_cl100k(text: str) -> int:
    if not text:
        return 0
    if _ENC is None:
        return 0
    return len(_ENC.encode(text))


def now_utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def ms_since(t0: float) -> float:
    return round((time.perf_counter() - t0) * 1000.0, 3)


@dataclass
class RagQueryLog:
    ts_utc: str
    source: str
    project: str
    collection: str
    query: str
    tokens_sent: int
    chunks_retrieved: List[Dict[str, Any]]
    top_k_requested: int
    top_k_returned: int
    retrieval_mode: str
    rerank_enabled: bool
    elapsed_ms: float
    extra: Optional[Dict[str, Any]] = None


def _day_file() -> Path:
    d = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    return LOG_DIR / f"rag_metrics_{d}.jsonl"


def write_rag_log(entry: RagQueryLog) -> None:
    with _day_file().open("a", encoding="utf-8") as f:
        f.write(json.dumps(asdict(entry), ensure_ascii=False) + "\n")
