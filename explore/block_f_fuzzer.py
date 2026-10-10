"""Block F: adversarial fuzzer over valid messages. Known command names only (case changes allowed);
mutates arguments, field count, numbers and the control. Flags any error code or response shape not seen before.
"""
import json
import random

from control import control
from probe import ROOT, budget, probe, reset

rng = random.Random(20261013)
BASES = ["CONSULTA;AC-0001", "DEPOSITO;AC-0001;500", "TRANSFER;AC-0001;AC-0002;600", "ANULA;OP-0001", "ALTA;Ana"]
NUM_MUTS = ["+5", "-5", "5.0", "05", "1e3", "0x10", " 5", "5 ", "٥", "9999999999", "10000000000", "5,0", "５"]


def mutate_args(fields):
    cmd, args = fields[0], fields[1:]
    op = rng.choice(["dup", "drop", "swap", "case_arg", "space", "long", "num", "case_cmd", "empty"])
    if op == "dup" and args:
        i = rng.randrange(len(args)); args.insert(i, args[i])
    elif op == "drop" and args:
        args.pop(rng.randrange(len(args)))
    elif op == "swap" and len(args) > 1:
        i, j = rng.sample(range(len(args)), 2); args[i], args[j] = args[j], args[i]
    elif op == "case_arg" and args:
        i = rng.randrange(len(args)); args[i] = args[i].lower()
    elif op == "space" and args:
        i = rng.randrange(len(args)); args[i] = rng.choice([" ", "", "\t"]) + args[i] + rng.choice([" ", ""])
    elif op == "long" and args:
        i = rng.randrange(len(args)); args[i] = args[i] + "Z" * 500
    elif op == "num":
        nums = [i for i, a in enumerate(args) if a.isdigit()]
        if nums:
            args[rng.choice(nums)] = rng.choice(NUM_MUTS)
    elif op == "case_cmd":
        cmd = rng.choice([cmd.lower(), cmd.capitalize(), cmd.swapcase()])
    elif op == "empty" and args:
        args[rng.randrange(len(args))] = ""
    return op, ";".join([cmd] + args)


def with_control(body):
    r = rng.random()
    if r < 0.6:
        return "valid", f"{body};{control(body)}"
    if r < 0.8:
        return "wrong", f"{body};{control(body) % 97 + 1}"
    return "malformed", f"{body};{rng.choice(['0' + str(control(body)), 'x', '100', '-1'])}"


def known_shapes():
    codes, shapes = set(), set()
    for line in (ROOT / "experimentos.jsonl").open():
        r = json.loads(line)["response"]
        if isinstance(r, dict):
            codes.add(r.get("error")); shapes.add(tuple(sorted(r)))
    return codes, shapes


def run(n_seqs=20, per_seq=10):
    codes, shapes = known_shapes()
    leads = []
    for i in range(n_seqs):
        seq = f"F-fuzz-{i:02d}"
        reset(seq)
        for body in ("ALTA;Ana", "ALTA;Beto", "DEPOSITO;AC-0001;500000"):
            probe(seq, "F setup", {"m": f"{body};{control(body)}"})
        for _ in range(per_seq):
            op, body = mutate_args(rng.choice(BASES).split(";"))
            kind, m = with_control(body)
            e, _ = probe(seq, f"F fuzz: mutation={op}, control={kind}", {"m": m})
            r = e["response"]
            if isinstance(r, dict) and (r.get("error") not in codes or tuple(sorted(r)) not in shapes):
                leads.append((e["id"], m, e["status"], r))
    print("NEW codes/shapes (leads):", len(leads))
    for lead in leads:
        print("  ", lead)
    budget()


if __name__ == "__main__":
    run()
