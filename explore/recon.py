"""Recon batch: determinism, framework fingerprint, default errors, auth behavior."""
import json

import sys

from probe import ROOT, budget, probe, reset

TAG = sys.argv[1] if len(sys.argv) > 1 else "recon"

EXAMPLES = [json.loads(l) for l in (ROOT / "material/pruebas/ejemplos.jsonl").open()]


def replay_examples(seq):
    reset(seq)
    diffs = []
    for ex in EXAMPLES:
        entry, _ = probe(seq, f"replay example n={ex['n']}: same status/body as morning recording", ex["request"])
        if entry["status"] != ex["status"] or entry["response"] != ex["response"]:
            diffs.append((ex["n"], ex["status"], ex["response"], entry["status"], entry["response"]))
    return diffs


print("== 1. determinism: replay examples twice ==")
for seq in (f"{TAG}-replay-1", f"{TAG}-replay-2"):
    diffs = replay_examples(seq)
    print(seq, "diffs:", len(diffs))
    for d in diffs:
        print("  ", d)

print("== 2. headers fingerprint ==")
reset(f"{TAG}-headers")
_, headers = probe(f"{TAG}-headers", "response headers reveal framework", {"m": "PING;64"})
print({k: v for k, v in headers.items() if k.lower() not in ("date",)})

print("== 3. default errors ==")
seq = f"{TAG}-errors"
reset(seq)
cases = [
    dict(hipotesis="unknown route returns framework default 404", method="GET", path="/does-not-exist"),
    dict(hipotesis="GET on /msg is rejected", method="GET", path="/msg"),
    dict(hipotesis="POST unknown route", method="POST", path="/nope", request={"m": "PING;64"}),
    dict(hipotesis="non-JSON body on /msg", raw_body="hola"),
    dict(hipotesis="JSON body without m", request={"x": "PING;64"}),
    dict(hipotesis="m is not a string", request={"m": 123}),
    dict(hipotesis="empty m", request={"m": ""}),
    dict(hipotesis="GET /health with token", method="GET", path="/health"),
]
for c in cases:
    entry, h = probe(seq, **c)
    print(f"{c.get('method','POST')} {c.get('path','/msg')} {c.get('request', c.get('raw_body'))!r} -> {entry['status']} {entry['response']!r} ct={h.get('content-type')}")

print("== 4. auth ==")
seq = f"{TAG}-auth"
reset(seq)
for token, label in ((None, "no token"), ("wrong-token-123", "wrong token")):
    for method, path, body in (("POST", "/msg", {"m": "PING;64"}), ("POST", "/__reset", None),
                               ("GET", "/health", None), ("GET", "/does-not-exist", None)):
        entry, h = probe(seq, f"{label} on {method} {path}", body, method=method, path=path, token=token)
        print(f"{label:12} {method} {path:16} -> {entry['status']} {entry['response']!r}")

budget()
