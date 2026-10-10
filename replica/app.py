"""HTTP layer of the replica. Self-contained: no credentials or network calls to the original service."""
import json
import os
import threading

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from engine import State, handle

TEAM_TOKEN = os.environ.get("TEAM_TOKEN", "")
print(f"TEAM_TOKEN set: {bool(TEAM_TOKEN)} (length {len(TEAM_TOKEN)})", flush=True)  # never the value
ROUTES = {("GET", "/health"), ("POST", "/__reset"), ("POST", "/msg")}

app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
state = State()
lock = threading.Lock()


def reply(status, body):
    return JSONResponse(body, status_code=status)


@app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"])
async def catch_all(request: Request, path: str):
    global state
    route = (request.method, "/" + path)
    if route not in ROUTES:
        return reply(404, {"error": "E404", "mensaje": "ruta desconocida"})
    if not TEAM_TOKEN or request.headers.get("authorization") != f"Bearer {TEAM_TOKEN}":
        return reply(401, {"error": "E001", "mensaje": "no autorizado"})
    if route == ("GET", "/health"):
        return reply(200, {"ok": True})
    if route == ("POST", "/__reset"):
        with lock:
            state = State()
        return reply(200, {"ok": True})
    try:
        payload = json.loads(await request.body())
    except ValueError:
        return reply(400, {"error": "E100", "mensaje": "json inválido"})
    m = payload.get("m") if isinstance(payload, dict) else None
    if not isinstance(m, str):
        return reply(400, {"error": "E102", "mensaje": "falta m"})
    with lock:
        return reply(*handle(state, m))
