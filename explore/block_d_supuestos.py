"""Block D: open assumptions — same-holder matching, amount upper bound, error order, id formats, cumulative limit."""
from control import control
from probe import budget, probe, reset


def send(seq, body, h):
    e, _ = probe(seq, h, {"m": f"{body};{control(body)}"})
    print(f"  {e['id']:>5} {body[:44]:44} -> {e['status']} {e['response']}")
    return e


print("== same holder matching")
for a, b, label in [("Beto", "BETO", "case"), ("Beto", "Beto ", "trailing space"), ("Lucía", "Lucia", "accent"),
                    ("Ana", "Ana", "exact, more evidence")]:
    seq = f"D-holder-{label.split()[0]}"
    reset(seq)
    send(seq, f"ALTA;{a}", f"same-holder rule ({label}): first account")
    send(seq, f"ALTA;{b}", f"same-holder rule ({label}): second account")
    send(seq, "DEPOSITO;AC-0001;300000", "fund source")
    send(seq, "TRANSFER;AC-0001;AC-0002;150000", f"150000 between '{a}' and '{b}': OK = same holder, E506 = different")

print("== amount upper bound (DEPOSITO)")
seq = "D-amount"
reset(seq)
send(seq, "ALTA;Ana", "setup account")
lo, hi = 500000, 999999999999  # lo accepted (cmd-transfer), hi rejected E303
while hi - lo > 1:
    mid = (lo + hi) // 2
    e = send(seq, f"DEPOSITO;AC-0001;{mid}", f"amount upper bound: binary search, trying {mid}")
    if e["status"] == 200:
        lo = mid
    else:
        hi = mid
print(f"  max accepted deposit {lo}, first rejected {hi}")

print("== error order in TRANSFER")
seq = "D-order"
reset(seq)
send(seq, "ALTA;Ana", "setup AC-0001")
for body, h in [("TRANSFER;AC-0009;AC-0009;abc", "E303 vs E304 vs E401 (all three faults)"),
                ("TRANSFER;AC-0009;AC-0009;10", "E304 vs E401 (same missing account)"),
                ("TRANSFER;AC-0001;AC-0001;abc", "E303 vs E304"),
                ("TRANSFER;AC-0001;AC-0009;100001", "E401 vs E506"),
                ("TRANSFER;AC-0009;AC-0001;abc", "E303 vs E401")]:
    send(seq, body, h)

print("== id formats")
seq = "D-ids"
reset(seq)
send(seq, "ALTA;Ana", "setup AC-0001")
send(seq, "DEPOSITO;AC-0001;10", "setup OP-0001")
for body in ["CONSULTA;ac-0001", "CONSULTA;AC-1", "CONSULTA;AC-00001", "CONSULTA;AC0001", "CONSULTA;AC-0001 ",
             "CONSULTA;XX-0001", "ANULA;op-0001", "ANULA;OP-1"]:
    send(seq, body, "id format variant: normalized or literal?")

print("== cumulative transfer limit")
seq = "D-cumulative"
reset(seq)
send(seq, "ALTA;Ana", "setup AC-0001")
send(seq, "ALTA;Beto", "setup AC-0002")
for _ in range(6):
    send(seq, "DEPOSITO;AC-0001;100000", "fund 600000 in steps")
for i in range(5):
    send(seq, "TRANSFER;AC-0001;AC-0002;100000", f"transfer #{i + 1} of 100000: any cumulative limit?")
budget()
