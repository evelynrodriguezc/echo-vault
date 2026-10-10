"""Control format (E201 vs E202) and error precedence when one message has several faults."""
from control import control
from probe import budget, probe, reset


def ok(body):
    return f"{body};{control(body)}"


def bad(body):
    return f"{body};{(control(body) % 97) + 1 if control(body) < 98 else 2}"  # valid range, wrong value


V = control("CONSULTA;AC-0001")  # 14
FORMAT = [
    (f"CONSULTA;AC-0001;0{V}", "zero-padded valid control '014' accepted?"),
    (f"CONSULTA;AC-0001;00{V}", "'0014' accepted?"),
    ("CONSULTA;AC-0005;02", "'02' for valid 2 accepted?"),
    (f"CONSULTA;AC-0001; {V}", "leading space in control -> E201 or accepted?"),
    (f"CONSULTA;AC-0001;{V} ", "trailing space in control"),
    (f"CONSULTA;AC-0001;+{V}", "plus sign in control"),
    (f"CONSULTA;AC-0001;-{V}", "negative control"),
    ("CONSULTA;AC-0001;1a", "letter in control -> E201"),
    ("CONSULTA;AC-0001;", "empty control field -> E103 or E201?"),
    (f"CONSULTA;AC-0001;1{V}", "3-digit control 114 -> E201 or E202?"),
    (f"CONSULTA;AC-0001;{V}.0", "decimal control"),
    ("CONSULTA;AC-0001;99", "out-of-range 99 (never valid) -> E202?"),
    ("CONSULTA;AC-0001", "no control field: last field AC-0001 read as control -> E201?"),
    ("CONSULTA", "single field -> E103 falta control?"),
    ("PING", "PING without control"),
]
PRECEDENCE = [
    (ok("SALDOS;AC-0001"), "unknown command + valid control -> E301"),
    (bad("SALDOS;AC-0001"), "unknown command + wrong control: E301 or E202 first?"),
    ("SALDOS;AC-0001;5X", "unknown command + malformed control: E301 or E201 first?"),
    (ok("ALTA;Lucia;Gomez"), "bad arity + valid control -> E302"),
    (bad("ALTA;Lucia;Gomez"), "bad arity + wrong control: E302 or E202 first?"),
    ("ALTA;Lucia;Gomez;5X", "bad arity + malformed control: E302 or E201 first?"),
    (bad("CONSULTA;AC-0009"), "missing account + wrong control -> E202 first (expected)"),
    (ok(";AC-0001"), "empty command + valid control"),
    (ok("consulta ;AC-0001"), "space after command name"),
    (ok("SALDOS"), "unknown command with no args + valid control"),
    (ok("CONSULTA"), "known command with no args (arity) + valid control"),
]
for seq, cases in (("format-control", FORMAT), ("precedence", PRECEDENCE)):
    reset(seq)
    for m, h in cases:
        e, _ = probe(seq, h, {"m": m})
        print(f"{m!r:32} -> {e['status']} {e['response']}")
budget()
