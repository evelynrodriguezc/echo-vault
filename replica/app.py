"""HTTP layer of the replica. Self-contained: no credentials or network calls to the original service."""
import json
import os
import threading

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from engine import RULES, State, err, handle

TEAM_TOKEN = os.environ.get("TEAM_TOKEN", "")
print(f"TEAM_TOKEN set: {bool(TEAM_TOKEN)} (length {len(TEAM_TOKEN)})", flush=True)  # never the value
ROUTES = {("GET", "/health"), ("POST", "/__reset"), ("POST", "/msg")}
RAILWAY_HEALTHCHECK_HOST = "healthcheck.railway.app"
MAX_BODY = RULES["limits"]["max_body_bytes"]  # larger raw body -> 413 E101 (checked after route and auth)

app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
state = State()
lock = threading.Lock()


def reply(status, body):
    return JSONResponse(body, status_code=status)


@app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS", "TRACE"])
async def catch_all(request: Request, path: str):
    global state
    route = (request.method, "/" + path)
    if route not in ROUTES:
        return reply(*err("E404"))
    if route == ("GET", "/health") and request.headers.get("host") == RAILWAY_HEALTHCHECK_HOST:
        return reply(200, {"ok": True})  # platform healthcheck sends no token; any other host still needs one
    if not TEAM_TOKEN or request.headers.get("authorization", "").strip() != f"Bearer {TEAM_TOKEN}":
        return reply(*err("E001"))
    if route == ("GET", "/health"):
        return reply(200, {"ok": True})
    if route == ("POST", "/__reset"):
        with lock:
            state = State()
        return reply(200, {"ok": True})
    raw = await request.body()
    if len(raw) > MAX_BODY:
        return reply(*err("E101"))
    try:
        payload = json.loads(raw)
    except ValueError:
        return reply(*err("E100"))
    m = payload.get("m") if isinstance(payload, dict) else None
    if not isinstance(m, str):
        return reply(*err("E102"))
    with lock:
        return reply(*handle(state, m))


STANDARD_METHODS = {"GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS", "TRACE"}
fastapi_app = app


async def app(scope, receive, send):  # noqa: F811
    """The original answers non-standard methods (e.g. FOO) with 400 and an empty body, before routing."""
    if scope["type"] == "http" and scope["method"] not in STANDARD_METHODS:
        await send({"type": "http.response.start", "status": 400, "headers": [(b"content-length", b"0")]})
        await send({"type": "http.response.body", "body": b""})
        return
    await fastapi_app(scope, receive, send)
