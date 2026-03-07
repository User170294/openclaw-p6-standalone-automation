import json
import urllib.parse
import urllib.request

PIPE_NAME = r"\\.\pipe\LilitASPluginPipe"
BASE_URL = "http://localhost:18850"


def _pipe_request(path, method="GET", query=None, timeout=5):
    payload = {
        "method": method,
        "path": path,
        "query": query or {},
    }
    req = (json.dumps(payload, ensure_ascii=False) + "\n").encode("utf-8")

    with open(PIPE_NAME, "r+b", buffering=0) as pipe:
        pipe.write(req)

        buf = bytearray()
        while True:
            b = pipe.read(1)
            if not b:
                break
            if b == b"\n":
                break
            buf.extend(b)

    if not buf:
        raise RuntimeError("empty response from pipe")

    envelope = json.loads(buf.decode("utf-8"))
    status = int(envelope.get("status", 500))
    body_text = envelope.get("body", "{}")
    body = json.loads(body_text)
    if status >= 400:
        raise RuntimeError(f"Pipe request failed ({status}): {body}")
    return body


def _http_request(path, method="GET", query=None, timeout=5):
    url = f"{BASE_URL}{path}"
    if query:
        url += "?" + urllib.parse.urlencode(query)

    req = urllib.request.Request(url=url, method=method)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())


def _request(path, method="GET", query=None, timeout=5):
    try:
        return _pipe_request(path, method=method, query=query, timeout=timeout)
    except Exception:
        return _http_request(path, method=method, query=query, timeout=timeout)


def ping():
    return _request("/ping", timeout=5)


def status():
    return _request("/status", timeout=5)


def get_elementos(tipo=None):
    query = {"tipo": tipo} if tipo else None
    return _request("/elementos", query=query, timeout=10)


def get_elemento(handle):
    return _request(f"/elemento/{handle}", timeout=5)


if __name__ == "__main__":
    print("Ping:", ping())
    print("Status:", status())
    print("Elementos:", get_elementos())