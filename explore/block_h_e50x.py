"""Block H: hunt the unseen business errors E501–E505 with state rules we never triggered.
Identical consecutive requests are interleaved with CONSULTA so the repeat guard does not stop the batch.
"""
from control import control
from probe import budget, probe, reset

NEW = []


def send(seq, body, h):
    e, _ = probe(seq, h, {"m": f"{body};{control(body)}"})
    r = e["response"]
    code = r.get("error") if isinstance(r, dict) else None
    flag = "  <-- NEW" if code and code not in {"E104", "E202", "E301", "E302", "E303", "E304", "E401", "E402", "E506", "E507"} else ""
    if flag:
        NEW.append((e["id"], body, e["status"], r))
    print(f"  {e['id']:>5} {body[:42]:42} -> {e['status']} {r}{flag}")
    return r


def block(name, steps):
    print("==", name)
    reset(name)
    for body, h in steps:
        send(name, body, h)


block("H-holder-many", [x for i in range(10) for x in (
    ("ALTA;Ana", f"many accounts for one holder: #{i + 1}"), (f"CONSULTA;AC-{i + 1:04d}", "break repeats"))])

block("H-op-count", [("ALTA;Ana", "setup"), ("ALTA;Beto", "setup"), ("DEPOSITO;AC-0001;5000", "fund")] +
      [(f"TRANSFER;AC-0001;AC-0002;{i + 1}", f"operation count limit per account: transfer #{i + 1}") for i in range(15)])

block("H-annul-spent", [
    ("ALTA;Ana", "setup"), ("ALTA;Beto", "setup"), ("ALTA;Carla", "setup"),
    ("DEPOSITO;AC-0001;1000", "OP-0001"), ("TRANSFER;AC-0001;AC-0002;600", "OP-0002 Ana->Beto"),
    ("TRANSFER;AC-0002;AC-0003;600", "OP-0003 Beto spends it"),
    ("ANULA;OP-0002", "annul a transfer whose destination already spent the money"),
    ("CONSULTA;AC-0002", "destination balance after"), ("ANULA;OP-0003", "annul the spending transfer"),
    ("ANULA;OP-0001", "annul the original deposit (chain)"), ("CONSULTA;AC-0001", "source balance after chain"),
    ("ANULA;OP-0002", "annul again (already annulled)")])

block("H-overflow", [("ALTA;Ana", "setup")] + [x for i in range(12) for x in (
    (f"DEPOSITO;AC-0001;{9999999999 - i}", f"balance overflow / max balance: deposit #{i + 1}"),)] +
    [("CONSULTA;AC-0001", "balance after ~1.2e11 deposited")])

block("H-negative", [
    ("ALTA;Ana", "setup"), ("ALTA;Beto", "setup"), ("DEPOSITO;AC-0001;1000", "OP-0001"),
    ("TRANSFER;AC-0001;AC-0002;1000", "move all"), ("ANULA;OP-0001", "annul deposit -> Ana at -1000"),
    ("CONSULTA;AC-0001", "negative balance"), ("TRANSFER;AC-0001;AC-0002;1", "transfer from negative balance"),
    ("DEPOSITO;AC-0001;500", "deposit into negative account"), ("CONSULTA;AC-0001", "balance after deposit"),
    ("ANULA;OP-0002", "annul transfer while source is negative")])

block("H-boundary", [
    ("ALTA;Ana", "setup"), ("ALTA;Beto", "setup"), ("DEPOSITO;AC-0001;600", "fund 600"),
    ("TRANSFER;AC-0001;AC-0002;601", "one above balance -> E507"), ("TRANSFER;AC-0001;AC-0002;600", "exactly the balance"),
    ("CONSULTA;AC-0001", "zero after")])

block("H-same-holder-max", [
    ("ALTA;Ana", "setup"), ("ALTA;Ana", "setup same holder"), ("DEPOSITO;AC-0001;9999999999", "fund max"),
    ("TRANSFER;AC-0001;AC-0002;9999999999", "same holder, max amount: any other limit?"),
    ("CONSULTA;AC-0002", "after")])

print("== H-lockout")
reset("H-lockout")
send("H-lockout", "ALTA;Ana", "setup")
for i in range(6):
    wrong = (control("CONSULTA;AC-0001") + 1 + i) % 97  # always 1-2 digits, never the valid value
    e, _ = probe("H-lockout", f"too many wrong controls lock the account? attempt {i + 1}", {"m": f"CONSULTA;AC-0001;{wrong}"})
    print(f"  {e['id']:>5} wrong control {wrong} -> {e['status']} {e['response']}")
send("H-lockout", "CONSULTA;AC-0001", "valid request after 6 wrong controls")

print("NEW CODES:", NEW)
budget()
