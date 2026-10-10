"""Probe the original black-box service and log every request to experimentos.jsonl."""
import json
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LOG = ROOT / "experimentos.jsonl"
DAILY_LIMIT = 8000
MIN_INTERVAL = 0.11  # stay under 10 requests per second


def _load_env():
    env = {}
    for line in (ROOT / ".env").read_text().splitlines():
        if "=" in line and not line.lstrip().startswith("#"):
            key, value = line.split("=", 1)
            env[key.strip()] = value.strip()
    return env


ENV = _load_env()
BASE = ENV["BLACKBOX_URL"].rstrip("/")
TOKEN = ENV["BLACKBOX_TOKEN"]
_last_call = 0.0


def _next_id():
    if not LOG.exists():
        return 1
    return sum(1 for _ in LOG.open()) + 1


def send(method, path, body=None, token=TOKEN, raw_body=None, content_type="application/json"):
    """Send one request; return (status, headers, text). Not logged."""
    global _last_call
    wait = MIN_INTERVAL - (time.time() - _last_call)
    if wait > 0:
        time.sleep(wait)
    data = raw_body.encode() if raw_body is not None else (json.dumps(body).encode() if body is not None else None)
    req = urllib.request.Request(BASE + path, data=data, method=method)
    if data is not None and content_type:
        req.add_header("Content-Type", content_type)
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    _last_call = time.time()
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return r.status, _lower(r.headers), r.read().decode()
    except urllib.error.HTTPError as e:
        return e.code, _lower(e.headers), e.read().decode()


def _lower(headers):
    return {k.lower(): v for k, v in headers.items()}


def probe(seq, hipotesis, request=None, method="POST", path="/msg", token=TOKEN,
          raw_body=None, content_type="application/json", conclusion=None):
    """Send one request to the original and append it to the experiment log."""
    status, headers, text = send(method, path, request, token, raw_body, content_type)
    rate_limited = headers.get("x-frontier-infra") == "rate-limit"
    try:
        response = json.loads(text)
    except ValueError:
        response = None
    entry = {
        "id": _next_id(),
        "seq": seq,
        "x_req": headers.get("x-req"),
        "hipotesis": hipotesis,
        "request": request if raw_body is None else raw_body,
        "status": status,
        "response": response if response is not None else text,
        "conclusion": conclusion,
        "method": method,
        "path": path,
        "auth": "own" if token == TOKEN else ("none" if not token else "other"),
        "ts": time.strftime("%Y-%m-%dT%H:%M:%S"),
    }
    if rate_limited:
        entry["infra"] = "rate-limit"
    with LOG.open("a") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    return entry, headers


def reset(seq):
    return probe(seq, "reset to initial state", None, path="/__reset")


def budget():
    used = sum(1 for _ in LOG.open()) if LOG.exists() else 0
    print(f"requests used: {used} / {DAILY_LIMIT} (remaining {DAILY_LIMIT - used})")
