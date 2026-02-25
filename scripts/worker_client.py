"""
worker_client.py
Cliente TCP loopback para project_query_worker.py
"""

import json
import os
import socket
import subprocess
from pathlib import Path
from typing import Any, Dict, Optional

PID_JSON_PATH = Path("data/worker.pid.json")
DEFAULT_TIMEOUT_S = 30.0


def _timeout_s() -> float:
    raw = os.getenv("WORKER_TIMEOUT_S", "").strip()
    if not raw:
        return DEFAULT_TIMEOUT_S
    try:
        v = float(raw)
        return v if v > 0 else DEFAULT_TIMEOUT_S
    except Exception:
        return DEFAULT_TIMEOUT_S


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
        # Si existe proceso, tasklist en CSV devuelve fila empezando con comillas:
        # "python.exe","1234",...
        return out.startswith('"')
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def _safe_unlink(path: Path) -> None:
    try:
        if path.exists():
            path.unlink()
    except Exception:
        pass


def read_worker_meta(pid_json_path: Path = PID_JSON_PATH) -> Optional[Dict[str, Any]]:
    if not pid_json_path.exists():
        return None
    try:
        meta = json.loads(pid_json_path.read_text(encoding="utf-8-sig"))
    except Exception:
        return None

    pid = int(meta.get("pid", 0) or 0)
    host = str(meta.get("host", "127.0.0.1"))
    port = int(meta.get("port", 0) or 0)
    if pid <= 0 or port <= 0:
        return None
    if not is_pid_alive(pid):
        _safe_unlink(pid_json_path)
        return None
    return meta


def is_worker_alive(pid_json_path: Path = PID_JSON_PATH) -> bool:
    return read_worker_meta(pid_json_path) is not None


def send_request(
    request_obj: Dict[str, Any],
    pid_json_path: Path = PID_JSON_PATH,
    timeout_s: Optional[float] = None,
) -> Dict[str, Any]:
    meta = read_worker_meta(pid_json_path)
    if meta is None:
        raise RuntimeError("worker_not_running")

    host = str(meta.get("host", "127.0.0.1"))
    port = int(meta.get("port"))
    timeout = _timeout_s() if timeout_s is None else timeout_s

    payload = (json.dumps(request_obj, ensure_ascii=False) + "\n").encode("utf-8")

    with socket.create_connection((host, port), timeout=timeout) as s:
        s.settimeout(timeout)
        s.sendall(payload)

        data = b""
        while b"\n" not in data:
            chunk = s.recv(4096)
            if not chunk:
                break
            data += chunk

    line = data.decode("utf-8", errors="replace").strip()
    if not line:
        raise RuntimeError("empty_worker_response")
    try:
        resp = json.loads(line)
    except Exception as e:
        raise RuntimeError(f"invalid_worker_response: {e}") from e
    return resp


if __name__ == "__main__":
    # smoke quick manual:
    # python scripts/worker_client.py '{"request_id":"1","project":"OT-1844","ask":"estado actual","top":3,"hybrid":true,"rerank":true}'
    import sys
    if len(sys.argv) < 2:
        print("Usage: python scripts/worker_client.py '<json_request>'")
        raise SystemExit(1)
    req = json.loads(sys.argv[1])
    out = send_request(req)
    print(json.dumps(out, ensure_ascii=False))
