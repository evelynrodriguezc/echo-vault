"""Canary: replay a few fixed sequences against the original and diff them with the replica's prediction.

Every request goes through probe() (logged, version-tagged). Any diff means the service changed or the
replica is wrong: either way it is a lead. Usage: PROBE_VERSION=v1 python3 explore/canary.py
"""
import json
import sys
import time
from pathlib import Path

from control import control
from probe import ROOT, budget, probe, reset

sys.path.insert(0, str(ROOT / "replica"))
import engine  # noqa: E402  (offline prediction only; the replica never calls the original)


def public_examples():
    """The 20 public example messages: from the challenge material if present, else from our logged replay of them."""
    material = ROOT / "material/pruebas/ejemplos.jsonl"
    if material.exists():
        return [e["request"]["m"] for e in map(json.loads, material.open())]
    log = map(json.loads, (ROOT / "experimentos.jsonl").open())
    return [e["request"]["m"] for e in log if e["seq"] == "recon2-replay-1" and e["path"] == "/msg"]


EXAMPLES = public_examples()


def msgs(*bodies):
    return [f"{b};{control(b)}" for b in bodies]


SEQUENCES = {
    "examples": EXAMPLES,
    "money": msgs("ALTA;Ana", "ALTA;Ana", "ALTA;Beto", "DEPOSITO;AC-0001;300000", "TRANSFER;AC-0001;AC-0002;150000",
                  "TRANSFER;AC-0001;AC-0003;100001", "TRANSFER;AC-0003;AC-0001;5", "ANULA;OP-0001",
                  "CONSULTA;AC-0001", "DEPOSITO;AC-0001;9999999999", "CONSULTA;AC-0002"),
    "errors": ["PING;XX", "CONSULTA", "CONSULTA;AC-0001;014", "consult;AC-0001;" + str(control("consult;AC-0001")),
               "DEPOSITO;AC-0001;0;" + str(control("DEPOSITO;AC-0001;0")), "ALTA;Lucía;14"],
}


def run():
    stamp = time.strftime("%H%M")
    diffs = []
    for name, sequence in SEQUENCES.items():
        seq = f"canary-{stamp}-{name}"
        reset(seq)
        state = engine.State()
        for m in sequence:
            e, _ = probe(seq, f"canary {name}: original still matches the replica model", {"m": m})
            want = engine.handle(state, m)
            if (e["status"], e["response"]) != want:
                diffs.append((e["id"], m, (e["status"], e["response"]), want))
    print(f"canary {stamp}: {len(diffs)} diffs")
    for d in diffs:
        print("  DIFF id=%s m=%r original=%s replica=%s" % d)
    budget()
    return diffs


if __name__ == "__main__":
    sys.exit(1 if run() else 0)
