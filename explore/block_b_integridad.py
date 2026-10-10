"""Block B: integrity edge cases — non-ASCII letters, whitespace, odd separators, unicode digits."""
from control import control
from probe import budget, probe, reset


def ok(body):
    return f"{body};{control(body)}"


CASES = [
    (ok("ALTA;Lucía"), "accent: control computed ignoring 'í' -> accepted?"),
    (f"ALTA;Lucía;{control('ALTA;Lucia')}", "accent: control computed mapping 'í'->'i' -> accepted?"),
    (ok("ALTA;Muñoz"), "ñ ignored in control?"),
    (f"ALTA;Muñoz;{control('ALTA;Munoz')}", "ñ mapped to n?"),
    (ok("ALTA;Ana\tB"), "tab inside a field"),
    (ok("ALTA;Ana\nB"), "newline inside a field"),
    (ok("ALTA; Ana"), "leading space in name field"),
    (ok("CONSULTA; AC-0001"), "space before account id: trimmed or literal?"),
    (ok(" PING"), "leading space before command"),
    ("PING;1 ", "trailing space after control (PING ignores value)"),
    ("CONSULTA,AC-0001,14", "comma separators -> single field -> E103?"),
    ("CONSULTA|AC-0001|14", "pipe separators"),
    (";", "only separator"),
    (";;", "two separators"),
    ("CONSULTA;AC-0001;١٤", "arabic-indic digits as control -> E201?"),
    (ok("CONSULTA;AC-000١"), "arabic-indic digit inside account id"),
    (ok("ALTA;Ana_B-C.D"), "punctuation in name"),
    (ok("ALTA;" + "😀"), "emoji name"),
    (ok("ALTA2;Ana"), "digit in command name"),
    (ok("ALTA;123"), "numeric-only name"),
    ("PING;", "PING with empty control -> E104"),
    ("PING;XX", "PING with letters as control (README example)"),
    ("PING;123", "PING with 3-digit control"),
]
seq = "B-integridad"
reset(seq)
for m, h in CASES:
    e, _ = probe(seq, h, {"m": m})
    print(f"{e['id']:>5} {m!r:34} -> {e['status']} {e['response']}")
budget()
