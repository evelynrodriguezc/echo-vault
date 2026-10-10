"""Block L (v2): exact new TRANSFER limit (fresh sequence per attempt so the E510 lock cannot interfere),
same-holder exemption, and E510 lock details. Usage: PROBE_VERSION=v2 python3 block_l_v2_details.py
"""
from control import control
from probe import budget, probe, reset


def ok(body):
    return {"m": f"{body};{control(body)}"}


def send(seq, hyp, body):
    e, _ = probe(seq, f"v2 detail: {hyp}", ok(body))
    print(f"  {e['id']:>5} {seq:18} {body:38} -> {e['status']} {e['response']}")
    return e


def fresh_transfer(amount, holder2="Beto"):
    seq = f"L1-limit-{amount}"
    reset(seq)
    send(seq, "setup", "ALTA;Ana")
    send(seq, "setup", f"ALTA;{holder2}")
    send(seq, "setup", "DEPOSITO;AC-0001;9999999999")
    return send(seq, f"new transfer limit: {amount} ({'same' if holder2 == 'Ana' else 'different'} holder)",
                f"TRANSFER;AC-0001;AC-0002;{amount}")


print("== 1. new TRANSFER limit (binary search 50000 ok .. 100000 E506)")
lo, hi = 50000, 100000
while hi - lo > 1:
    mid = (lo + hi) // 2
    if fresh_transfer(mid)["status"] == 200:
        lo = mid
    else:
        hi = mid
print(f"  max accepted {lo}, first E506 {hi}")
print("== same holder above the new limit")
fresh_transfer(150000, holder2="Ana")

print("== 2. E510 lock details")
seq = "L2-lock"
reset(seq)
for b in ["ALTA;Ana", "ALTA;Beto", "ALTA;Carla", "DEPOSITO;AC-0001;300000", "DEPOSITO;AC-0003;300000"]:
    send(seq, "setup", b)
for amt in (120000, 130000, 140000):
    send(seq, "3 consecutive E506 from AC-0001", f"TRANSFER;AC-0001;AC-0002;{amt}")
for hyp, b in [("locked: transfer out (intentos 1?)", "TRANSFER;AC-0001;AC-0002;1000"),
               ("locked: transfer out again (intentos 2?)", "TRANSFER;AC-0001;AC-0002;1001"),
               ("locked account: deposit?", "DEPOSITO;AC-0001;100"),
               ("locked account: consult?", "CONSULTA;AC-0001"),
               ("other account of same token: transfer out?", "TRANSFER;AC-0003;AC-0002;1000"),
               ("incoming transfer to locked account?", "TRANSFER;AC-0003;AC-0001;500"),
               ("annul a deposit of the locked account?", "ANULA;OP-0001"),
               ("locked: transfer out after other ops (intentos?)", "TRANSFER;AC-0001;AC-0002;1002"),
               ("balance locked account", "CONSULTA;AC-0001")]:
    send(seq, hyp, b)

seq = "L3-nonconsecutive"
reset(seq)
for b in ["ALTA;Ana", "ALTA;Beto", "DEPOSITO;AC-0001;300000"]:
    send(seq, "setup", b)
for hyp, b in [("E506 #1", "TRANSFER;AC-0001;AC-0002;120000"), ("valid in between", "TRANSFER;AC-0001;AC-0002;1000"),
               ("E506 #2", "TRANSFER;AC-0001;AC-0002;130000"), ("E506 #3", "TRANSFER;AC-0001;AC-0002;140000"),
               ("valid after non-consecutive E506s: locked?", "TRANSFER;AC-0001;AC-0002;1001"),
               ("E506 #4 (3rd consecutive if the valid one reset it)", "TRANSFER;AC-0001;AC-0002;150000"),
               ("valid again", "TRANSFER;AC-0001;AC-0002;1002")]:
    send(seq, hyp, b)
budget()
