"""Block E: long stateful sequences (8-12 steps) that stress state: negative balances, annul chains,
same-holder pairs, >9 accounts, faults interleaved mid-sequence (must not change state). Fixed seed.
"""
import random

from control import control
from probe import budget, probe, reset

rng = random.Random(20261012)


def step(seq, body, h, fault=None):
    m = f"{body};{control(body)}"
    if fault == "control":
        m = f"{body};{control(body) % 97 + 1}"
    elif fault == "arity":
        m = f"{body};x;{control(body + ';x')}"
    e, _ = probe(seq, h, {"m": m})
    return e["response"]


def run(n_seqs=20):
    for i in range(n_seqs):
        seq = f"E-long-{i:02d}"
        reset(seq)
        accounts, ops = [], []
        holders = rng.sample(["Ana", "Ana", "Beto", "Carla"], 3)  # often two accounts share a holder
        n_acc = rng.choice([2, 3, 3, 11])  # sometimes cross AC-0010
        for k in range(n_acc):
            r = step(seq, f"ALTA;{holders[k % 3]}", "E: create account")
            accounts.append(r["cuentaId"])
        for _ in range(rng.randint(8, 12) - min(n_acc, 4)):
            kind = rng.choices(["DEP", "TRF", "ANU", "CON", "FAULT"], [3, 4, 3, 2, 1])[0]
            a, b = rng.sample(accounts, 2)
            if kind == "DEP":
                r = step(seq, f"DEPOSITO;{a};{rng.choice([700, 50000, 100000, 9999999999])}", "E: deposit")
            elif kind == "TRF":
                r = step(seq, f"TRANSFER;{a};{b};{rng.choice([1, 600, 50000, 100000, 100001])}",
                         "E: transfer (may come from negative balance or between same-holder accounts)")
            elif kind == "ANU" and ops:
                r = step(seq, f"ANULA;{rng.choice(ops)}", "E: annul (chains, repeats, deposits already moved)")
            elif kind == "FAULT":
                r = step(seq, f"DEPOSITO;{a};500", "E: faulty message mid-sequence must not change state",
                         fault=rng.choice(["control", "arity"]))
            else:
                r = step(seq, f"CONSULTA;{a}", "E: balance check")
            if isinstance(r, dict) and "operacionId" in r:
                ops.append(r["operacionId"])
        for a in accounts[:4]:
            step(seq, f"CONSULTA;{a}", "E: final balance")
    budget()


if __name__ == "__main__":
    run()
