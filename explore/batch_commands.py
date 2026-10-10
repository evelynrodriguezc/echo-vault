"""Commands: ALTA, DEPOSITO, TRANSFER, ANULA, CONSULTA — effects, limits, counters, odd amounts."""
from control import control
from probe import budget, probe, reset


def run(seq, steps):
    reset(seq)
    for body, hyp in steps:
        e, _ = probe(seq, hyp, {"m": f"{body};{control(body)}"})
        print(f"[{seq}] {body!r:40} -> {e['status']} {e['response']}")


run("cmd-alta", [
    ("ALTA;Ana", "ALTA creates AC-0001"),
    ("ALTA;Ana", "duplicate name allowed? -> AC-0002 or error"),
    ("ALTA;ANA", "case variant of name"),
    ("ALTA;Ana Maria", "name with space"),
    ("ALTA;Ana123", "name with digits"),
    ("ALTA;" + "X" * 40, "very long name (40 chars)"),
    ("ALTA;A", "one-letter name"),
    ("CONSULTA;AC-0001", "new account starts with saldo 0"),
    ("CONSULTA;AC-0006", "id of last created account"),
])
run("cmd-deposito", [
    ("ALTA;Ana", "setup AC-0001"),
    ("DEPOSITO;AC-0001;0", "zero amount"),
    ("DEPOSITO;AC-0001;-5", "negative amount"),
    ("DEPOSITO;AC-0001;1.5", "decimal amount"),
    ("DEPOSITO;AC-0001;007", "leading zeros amount"),
    ("DEPOSITO;AC-0001;abc", "non-numeric amount"),
    ("DEPOSITO;AC-0001;999999999999", "huge amount"),
    ("DEPOSITO;AC-0009;100", "nonexistent account"),
    ("DEPOSITO;AC-0009;abc", "nonexistent account + bad amount: which first?"),
    ("DEPOSITO;AC-0001;1", "OP counter after failed ops: OP-0001 or later?"),
    ("CONSULTA;AC-0001", "balance after all deposits"),
    ("DEPOSITO;AC-0001", "arity: missing amount"),
])
run("cmd-transfer", [
    ("ALTA;Ana", "setup AC-0001"),
    ("ALTA;Beto", "setup AC-0002"),
    ("DEPOSITO;AC-0001;500000", "fund AC-0001"),
    ("TRANSFER;AC-0001;AC-0002;120000", "first transfer 120000: per-op limit (fails) or cumulative (ok)?"),
    ("TRANSFER;AC-0001;AC-0002;100001", "just above 100000"),
    ("TRANSFER;AC-0001;AC-0002;100000", "exactly 100000"),
    ("TRANSFER;AC-0001;AC-0002;100000", "second 100000: cumulative limit?"),
    ("TRANSFER;AC-0001;AC-0001;10", "same source and destination"),
    ("TRANSFER;AC-0001;AC-0009;10", "nonexistent destination"),
    ("TRANSFER;AC-0009;AC-0001;10", "nonexistent source"),
    ("TRANSFER;AC-0002;AC-0001;999999", "insufficient + over limit: E506 or E507 first?"),
    ("TRANSFER;AC-0001;AC-0002;0", "zero transfer"),
    ("CONSULTA;AC-0001", "balance source"),
    ("CONSULTA;AC-0002", "balance destination"),
])
run("cmd-anula", [
    ("ALTA;Ana", "setup AC-0001"),
    ("ALTA;Beto", "setup AC-0002"),
    ("DEPOSITO;AC-0001;1000", "OP-0001 deposit"),
    ("TRANSFER;AC-0001;AC-0002;600", "OP-0002 transfer"),
    ("ANULA;OP-0001", "annul deposit whose money was partly moved -> negative balance?"),
    ("CONSULTA;AC-0001", "balance after annulling deposit"),
    ("ANULA;OP-0002", "annul transfer"),
    ("CONSULTA;AC-0001", "balance after annulling transfer"),
    ("CONSULTA;AC-0002", "destination balance after annulling transfer"),
    ("ANULA;OP-0099", "annul nonexistent op"),
    ("ANULA;AC-0001", "annul with account id"),
    ("DEPOSITO;AC-0001;5", "OP counter after ANULA: OP-0003?"),
])
budget()
