"""Block A: HTTP entry layer — m length limit, body shapes, content types, paths/methods, auth header variants."""
from control import control
from probe import TOKEN, budget, probe, reset


def ok(body):
    return {"m": f"{body};{control(body)}"}


def show(e):
    r = e["response"]
    print(f"  {e['id']:>5} {e['status']} {r if isinstance(r, dict) else repr(r)[:80]}")
    return e


seq = "A-length2"
reset(seq)
for n in (4096, 10000):
    show(probe(seq, f"m length limit: ALTA with {n}-char name (valid control)", ok("ALTA;" + "X" * n))[0])

seq = "A-body"
reset(seq)
for raw, hyp in [("", "empty body"), ("null", "JSON null"), ("[]", "JSON array"), ('"PING;1"', "JSON string"),
                 ("123", "JSON number"), ('{"M":"PING;1"}', "key M uppercase"), ('{"m":null}', "m null"),
                 ('{"m":["PING;1"]}', "m array"), ('{"m":"PING;1","x":1}', "extra key accepted?"),
                 ('{"m":"x","m":"PING;1"}', "duplicate key: last wins?"), ('  {"m":"PING;1"}  ', "whitespace around JSON"),
                 ('{"m":"PING;1"', "truncated JSON"), ('{"m":true}', "m boolean"), ("{}", "empty object")]:
    show(probe(seq, f"body shape: {hyp}", raw_body=raw)[0])

seq = "A-ctype"
reset(seq)
for ct in (None, "text/plain", "application/x-www-form-urlencoded", "application/json; charset=latin1"):
    show(probe(seq, f"content type {ct!r} with valid JSON body", raw_body='{"m":"PING;1"}', content_type=ct)[0])

seq = "A-routes"
reset(seq)
for method, path in [("POST", "/msg/"), ("POST", "/MSG"), ("POST", "/msg?x=1"), ("POST", "//msg"), ("POST", "/msg/extra"),
                     ("GET", "/health/"), ("HEAD", "/health"), ("OPTIONS", "/msg"), ("GET", "/__reset"),
                     ("POST", "/health"), ("PUT", "/msg"), ("DELETE", "/msg"), ("GET", "/")]:
    body = {"m": "PING;1"} if method in ("POST", "PUT") else None
    show(probe(seq, f"route/method: {method} {path}", body, method=method, path=path)[0])

seq = "A-auth"
reset(seq)
for header in [f"bearer {TOKEN}", f"BEARER {TOKEN}", f"Bearer  {TOKEN}", f"Bearer {TOKEN} ", f"Token {TOKEN}",
               TOKEN, "Bearer", "Bearer ", f"Basic {TOKEN}"]:
    show(probe(seq, "auth header variant", {"m": "PING;1"}, auth_header=header)[0])
budget()
