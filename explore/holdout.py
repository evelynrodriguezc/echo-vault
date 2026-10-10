"""Record a hold-out set: random sequences shaped like the hidden set, never used to build the replica.

40 single requests, 45 sequences of 2-5, 15 of 6-12. Known commands only; fixed seed.
"""
import random

from control import control
from probe import budget, probe, reset

rng = random.Random(20261010)
NAMES = ["Lucia", "Mateo", "Ana", "Beto", "Carla", "Diego", "Elena", "Felipe"]


def acc(n):
    return f"AC-{n:04d}"


def amount(kind="any"):
    choices = ["valid"] * 6 + ["big", "limit", "invalid"]
    k = kind if kind != "any" else rng.choice(choices)
    if k == "valid":
        return str(rng.choice([1, 50, 700, 1000, 25000, 40000, 99999, 100000]))
    if k == "big":
        return str(rng.choice([100001, 120000, 250000, 500000]))
    if k == "limit":
        return "100000"
    return rng.choice(["0", "-5", "1.5", "007", "abc"])


def message(st):
    """Build one message body from the current (believed) state; st = {'accounts': n, 'ops': n}."""
    na, no = st["accounts"], st["ops"]
    any_acc = lambda: acc(rng.randint(1, max(na, 1) + 1))  # sometimes nonexistent
    cmd = rng.choices(["ALTA", "CONSULTA", "DEPOSITO", "TRANSFER", "ANULA", "PING"], [4, 3, 4, 4, 2, 1])[0]
    if cmd == "ALTA":
        return f"ALTA;{rng.choice(NAMES)}"
    if cmd == "CONSULTA":
        return f"CONSULTA;{any_acc()}"
    if cmd == "DEPOSITO":
        return f"DEPOSITO;{any_acc()};{amount()}"
    if cmd == "TRANSFER":
        src, dst = any_acc(), any_acc()
        return f"TRANSFER;{src};{dst};{amount()}"
    if cmd == "ANULA":
        return f"ANULA;OP-{rng.randint(1, max(no, 1) + 1):04d}"
    return "PING"


def mutate(body):
    """Return the full m: usually valid control, sometimes a fault."""
    r = rng.random()
    if r < 0.75:
        return f"{body};{control(body)}"
    if r < 0.82:
        return f"{body};{control(body) % 97 + 1}"  # wrong control
    if r < 0.86:
        return f"{body};0{control(body)}"  # malformed control
    if r < 0.90:
        head, _, rest = body.partition(";")
        b = f"{head.lower()};{rest}" if rest else head.lower()
        return f"{b};{control(b)}"  # lowercase command
    if r < 0.94:
        b = body + ";extra"
        return f"{b};{control(b)}"  # bad arity
    if r < 0.97:
        return f"{body};;{control(body)}"  # empty segment
    return body  # no control


def run():
    lengths = [1] * 40 + [rng.randint(2, 5) for _ in range(45)] + [rng.randint(6, 12) for _ in range(15)]
    for i, n in enumerate(lengths):
        seq = f"holdout-{i:03d}"
        reset(seq)
        st = {"accounts": 0, "ops": 0}
        for _ in range(n):
            m = mutate(message(st))
            e, _ = probe(seq, "hold-out: random sequence, not used for discovery", {"m": m})
            resp = e["response"]
            if isinstance(resp, dict) and "cuentaId" in resp:
                st["accounts"] += 1
            if isinstance(resp, dict) and "operacionId" in resp:
                st["ops"] += 1
    budget()


if __name__ == "__main__":
    run()
