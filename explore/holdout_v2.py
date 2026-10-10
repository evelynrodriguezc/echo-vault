"""Hold-out v2: money flows. Each sequence creates accounts, funds them, then mixes transfers near
the limit and the balance, annulments (incl. repeated) and balance checks. Valid controls only, so
every request exercises command semantics. Known commands only; fixed seed.
"""
import random

from control import control
from probe import budget, probe, reset

rng = random.Random(20261011)
NAMES = ["Lucia", "Mateo", "Ana", "Beto", "Carla", "Diego"]
AMOUNTS = [1, 500, 999, 10000, 40000, 50000, 99999, 100000, 100001, 150000, 250000]


def send(seq, body, hyp):
    e, _ = probe(seq, hyp, {"m": f"{body};{control(body)}"})
    return e["response"]


def run(n_seqs=30):
    for i in range(n_seqs):
        seq = f"holdout2-{i:03d}"
        reset(seq)
        accounts, ops = [], []
        for _ in range(rng.randint(2, 3)):
            r = send(seq, f"ALTA;{rng.choice(NAMES)}", "hold-out v2 setup: create account")
            accounts.append(r["cuentaId"])
        for a in rng.sample(accounts, rng.randint(1, len(accounts))):
            r = send(seq, f"DEPOSITO;{a};{rng.choice([50000, 120000, 300000])}", "hold-out v2 setup: fund account")
            ops.append(r.get("operacionId"))
        for _ in range(rng.randint(3, 8)):
            kind = rng.choices(["TRANSFER", "ANULA", "DEPOSITO", "CONSULTA"], [5, 2, 1, 2])[0]
            if kind == "TRANSFER":
                src, dst = rng.sample(accounts, 2)
                r = send(seq, f"TRANSFER;{src};{dst};{rng.choice(AMOUNTS)}", "hold-out v2: transfer near limit/balance")
            elif kind == "ANULA" and ops:
                r = send(seq, f"ANULA;{rng.choice(ops)}", "hold-out v2: annul existing op (maybe repeated)")
            elif kind == "DEPOSITO":
                r = send(seq, f"DEPOSITO;{rng.choice(accounts)};{rng.choice(AMOUNTS)}", "hold-out v2: deposit")
            else:
                r = send(seq, f"CONSULTA;{rng.choice(accounts)}", "hold-out v2: balance check")
            if isinstance(r, dict) and "operacionId" in r:
                ops.append(r["operacionId"])
        for a in accounts:
            send(seq, f"CONSULTA;{a}", "hold-out v2: final balance")
    budget()


if __name__ == "__main__":
    run()
