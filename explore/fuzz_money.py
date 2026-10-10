"""Differential fuzzer for long stateful sequences (6-12 steps): money flows, ANULA chains, same-holder pairs,
negative balances. Each step is sent to the original and compared live with the replica's prediction
(replica/engine.py, offline). Meant for after the incident, against v2.

Usage (from explore/):
    python3 fuzz_money.py --dry-run [--seqs 25]          # prints sequences, predictions and request count; sends nothing
    PROBE_VERSION=v2 PROBE_MAX=400 python3 fuzz_money.py [--seqs 25]
"""
import random
import sys
from pathlib import Path

from control import control

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "replica"))
import engine  # noqa: E402  (offline prediction only)

SEQS = int(sys.argv[sys.argv.index("--seqs") + 1]) if "--seqs" in sys.argv else 25
DRY = "--dry-run" in sys.argv
SEED = 20261014
HOLDERS = ["Ana", "Ana", "Beto", "Carla"]  # duplicate name: same-holder pairs are common
AMOUNTS = [1, 600, 1000, 50000, 99999, 100000, 100001, 150000, 9999999999]


def gen_sequence(rng):
    """Build one 6-12 step sequence, tracking the replica's state so steps reference real ids."""
    state, msgs = engine.State(), []

    def add(body):
        m = f"{body};{control(body)}"
        msgs.append(m)
        return engine.handle(state, m)

    for name in rng.sample(HOLDERS, rng.choice([2, 3])):
        add(f"ALTA;{name}")
    accounts = list(state.accounts)
    for acc in accounts[:2]:  # fund two accounts so transfers succeed in both directions
        add(f"DEPOSITO;{acc};{rng.choice([1000, 150000, 300000])}")
    target = rng.randint(6, 12) - len(accounts)  # leave room for the final balance checks
    while len(msgs) < target:
        a, b = rng.sample(accounts, 2)
        ops = list(state.ops)
        kind = rng.choices(["TRF", "ANU", "DEP", "CON", "NEG"], [5, 3, 2, 2, 3])[0]
        if kind == "TRF":
            add(f"TRANSFER;{a};{b};{rng.choice(AMOUNTS)}")
        elif kind == "ANU" and ops:
            add(f"ANULA;{rng.choice(ops)}")  # chains, repeats, annulments of money already moved
        elif kind == "DEP":
            add(f"DEPOSITO;{a};{rng.choice(AMOUNTS)}")
        elif kind == "NEG" and ops and len(msgs) + 3 <= target:
            other = rng.choice(accounts[1:])
            add(f"TRANSFER;{accounts[0]};{other};1000")  # move money out first...
            add(f"ANULA;{ops[0]}")  # ...then annul the deposit that funded it: negative balance
            add(f"TRANSFER;{accounts[0]};{other};1")  # transfer from a negative balance
        else:
            add(f"CONSULTA;{a}")
    for acc in accounts:
        add(f"CONSULTA;{acc}")
    return msgs


def predictions(msgs):
    state = engine.State()
    return [engine.handle(state, m) for m in msgs]


def main():
    rng = random.Random(SEED)
    sequences = [gen_sequence(rng) for _ in range(SEQS)]
    cost = sum(len(s) + 1 for s in sequences)  # + one reset each
    print(f"{SEQS} sequences, lengths {min(map(len, sequences))}-{max(map(len, sequences))}, planned requests: {cost}")
    if DRY:
        for i, msgs in enumerate(sequences[:3]):
            print(f"-- fuzz-money-{i:02d}")
            for m, (status, body) in zip(msgs, predictions(msgs)):
                print(f"   {m:44} -> {status} {body}")
        kinds = [m.split(";")[0] for s in sequences for m in s]
        print("message mix:", {k: kinds.count(k) for k in sorted(set(kinds))})
        return

    from probe import budget, probe, reset  # imported only for real runs (takes the prober lock)

    diffs = []
    for i, msgs in enumerate(sequences):
        seq = f"fuzz-money-{i:02d}"
        reset(seq)
        for m, want in zip(msgs, predictions(msgs)):
            e, _ = probe(seq, "differential fuzz (long stateful sequence): original vs replica prediction", {"m": m})
            if (e["status"], e["response"]) != want:
                diffs.append((e["id"], seq, m, (e["status"], e["response"]), want))
    print(f"diffs: {len(diffs)}")
    for d in diffs:
        print("  id=%s %s %r\n     original=%s\n     replica =%s" % d)
    budget()


if __name__ == "__main__":
    main()
