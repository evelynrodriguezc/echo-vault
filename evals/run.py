"""Replay logged sequences against the replica in-process and report exact-match rates per category.

Usage: .venv/bin/python evals/run.py [-v] [--version v1]   (lines without a version tag count as v1)
"""
import json
import os
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
os.environ["TEAM_TOKEN"] = "eval-team-token"
sys.path.insert(0, str(ROOT / "replica"))

import warnings  # noqa: E402

warnings.filterwarnings("ignore", message="Using `httpx` with `starlette.testclient`")  # cosmetic notice
from fastapi.testclient import TestClient  # noqa: E402

import app as replica  # noqa: E402

VERSION = sys.argv[sys.argv.index("--version") + 1] if "--version" in sys.argv else None
FIRST_VALID_ID = 83  # ids 1-82 were sent with a wrong token (see README, Log completeness)
TOKENS = {"own": "eval-team-token", "other": "wrong-token-123", "none": None}


def category(seq):
    for prefix, name in (("recon", "entrada-auth"), ("format", "integridad"), ("sweep", "integridad"),
                         ("control", "integridad"), ("precedence", "errores"), ("cmd", "comandos"), ("A-", "entrada-auth"), ("B-", "integridad"), ("C-", "comandos"), ("G-", "comandos"), ("D-", "supuestos"), ("E-", "secuencias-largas"), ("F-", "fuzzer"), ("H-", "estado-reglas"), ("N-", "comandos"), ("canary", "canario"), ("specprobe", "spec-probe"), ("holdout2", "holdout-money"), ("holdout", "holdout")):
        if seq.startswith(prefix):
            return name
    return "other"


def load_sequences():
    seqs = defaultdict(list)
    for line in (ROOT / "experimentos.jsonl").open():
        e = json.loads(line)
        if e["id"] < FIRST_VALID_ID or e.get("infra") == "rate-limit":
            continue
        if VERSION and e.get("version", "v1") != VERSION:
            continue
        seqs[e["seq"]].append(e)
    if VERSION not in (None, "v1"):
        return seqs  # the 20 public examples were recorded on the morning version
    examples_file = ROOT / "material/pruebas/ejemplos.jsonl"  # challenge material, not in the repo
    if not examples_file.exists():
        print("note: material/ not present; the 20 public examples are still covered by the logged replays "
              "recon2-replay-1/2 (ids 147-188)")
        return seqs
    examples = [json.loads(l) for l in examples_file.open()]
    seqs["ejemplos"] = [{"method": "POST", "path": "/__reset", "auth": "own", "request": None, "status": 200,
                         "response": {"ok": True}}] + [
        {"method": "POST", "path": "/msg", "auth": "own", **e} for e in examples]
    return seqs


def send(client, e):
    headers = {}
    if e.get("auth") == "custom":
        headers["Authorization"] = e["auth_header"].replace("<own>", TOKENS["own"])
    elif TOKENS[e.get("auth", "own")]:
        headers["Authorization"] = f"Bearer {TOKENS[e.get('auth', 'own')]}"
    content_type = e.get("content_type", "application/json")
    req = e["request"]
    if isinstance(req, str):
        if content_type:
            headers["Content-Type"] = content_type
        return client.request(e["method"], e["path"], content=req.encode(), headers=headers)
    if req is None:
        return client.request(e["method"], e["path"], headers=headers)
    headers["Content-Type"] = content_type or "application/json"
    return client.request(e["method"], e["path"], content=json.dumps(req).encode(), headers=headers)  # same bytes as the prober


def same(resp, e):
    if resp.status_code != e["status"]:
        return False
    try:
        return resp.json() == e["response"]
    except ValueError:
        return resp.text == e["response"]


def main(verbose):
    client = TestClient(replica.app)
    per_cat = defaultdict(lambda: [0, 0, 0, 0])  # seq pass, seq total, req pass, req total
    failures = []
    for seq, entries in load_sequences().items():
        cat = "ejemplos" if seq == "ejemplos" else category(seq)
        replica.state = replica.State()
        ok_all = True
        for e in entries:
            resp = send(client, e)
            ok = same(resp, e)
            per_cat[cat][2] += ok
            per_cat[cat][3] += 1
            if not ok:
                ok_all = False
                failures.append((cat, e.get("id"), e["request"], e["status"], e["response"], resp.status_code, resp.text))
        per_cat[cat][0] += ok_all
        per_cat[cat][1] += 1
    print(f"{'category':14} {'sequences':>12} {'requests':>14}")
    for cat, (sp, st, rp, rt) in sorted(per_cat.items()):
        print(f"{cat:14} {sp:>5}/{st:<5} {100*sp/st:5.1f}%  {rp:>5}/{rt:<5} {100*rp/rt:5.1f}%")
    print(f"failures: {len(failures)}")
    for f in failures[: (None if verbose else 10)]:
        print("  ", f)


if __name__ == "__main__":
    main("-v" in sys.argv)
