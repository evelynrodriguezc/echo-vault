"""Block C: E301 suggestion rule, PING arity, and the 8 approved candidate command names (manual, one each)."""
from control import control
from probe import budget, probe, reset


def ok(body):
    return {"m": f"{body};{control(body)}"}


SUGGEST = [  # (command, edit distance to the nearest known command)
    ("CONSULT", "del 1 -> CONSULTA"), ("CONSULTAS", "ins 1"), ("CONSLTA", "del 1 inside"), ("CONSULTE", "sub 1"),
    ("CONSUL", "del 2"), ("CONSULTASS", "ins 2"), ("DEPOSIT", "del 1 -> DEPOSITO"), ("DEPOSI", "del 2"),
    ("TRANSFERR", "ins 1"), ("TRANSFRE", "transposition (Levenshtein 2, Damerau 1)"), ("ALT", "del 1 -> ALTA"),
    ("AL", "del 2"), ("ANUL", "del 1 -> ANULA"), ("PIN", "del 1 -> PING"), ("PINGG", "ins 1"),
    ("ALTO", "sub 1 -> ALTA"), ("XLTA", "sub 1 at start"),
]
NEW = ["RETIRO", "SALDO", "EXTRACTO", "HISTORIAL", "MOVIMIENTOS", "BAJA", "LISTA", "AYUDA"]

seq = "C-sugerencia"
reset(seq)
for cmd, h in SUGGEST:
    e, _ = probe(seq, f"E301 suggestion rule: '{cmd}' ({h})", ok(f"{cmd};AC-0001"))
    print(f"{e['id']:>5} {cmd:12} -> {e['status']} {e['response']}")

seq = "C-ping"
reset(seq)
for body in ("PING;x", "PING;x;y"):
    e, _ = probe(seq, f"PING arity: '{body}' + control", ok(body))
    print(f"{e['id']:>5} {body:12} -> {e['status']} {e['response']}")

seq = "C-nuevos"
reset(seq)
for cmd in NEW:
    e, _ = probe(seq, f"candidate hidden command '{cmd}': E301 = does not exist; anything else = lead", ok(f"{cmd};AC-0001"))
    print(f"{e['id']:>5} {cmd:12} -> {e['status']} {e['response']}")
budget()
