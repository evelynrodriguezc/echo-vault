"""Block M-lock (v2): unobserved E510 details (CMD-14b). Three sequences, no HALT.
Usage: PROBE_VERSION=v2 python3 block_m_lock.py
"""
from control import control
from probe import budget, probe, reset


def run(seq, steps):
    reset(seq)
    for hyp, body in steps:
        e, _ = probe(seq, f"E510 detail: {hyp}", {"m": f"{body};{control(body)}"})
        print(f"  {e['id']:>5} {seq:12} {body:34} -> {e['status']} {e['response']}")


LOCK = [("E506 #1", "TRANSFER;AC-0001;AC-0002;60000"), ("E506 #2", "TRANSFER;AC-0001;AC-0002;70000"),
        ("E506 #3 -> locked", "TRANSFER;AC-0001;AC-0002;80000")]
run("M1-incoming", [("setup", "ALTA;Ana"), ("setup", "ALTA;Beto"), ("setup", "ALTA;Carla"),
                    ("setup", "DEPOSITO;AC-0001;1000"), ("setup", "DEPOSITO;AC-0003;1000")] + LOCK + [
    ("locked + amount over the limit: E510 or E506?", "TRANSFER;AC-0001;AC-0002;90000"),
    ("incoming transfer to the locked account", "TRANSFER;AC-0003;AC-0001;500"),
    ("after incoming: still locked?", "TRANSFER;AC-0001;AC-0002;100")])
run("M2-anula", [("setup", "ALTA;Ana"), ("setup", "ALTA;Beto"), ("setup", "DEPOSITO;AC-0001;1000")] + LOCK + [
    ("ANULA the locked account's deposit", "ANULA;OP-0001"),
    ("after ANULA: E510 (still locked) or E507 (unlocked, balance 0)?", "TRANSFER;AC-0001;AC-0002;100")])
run("M3-e507", [("setup", "ALTA;Ana"), ("setup", "ALTA;Beto"), ("setup", "DEPOSITO;AC-0001;1000"),
                ("E506 #1", "TRANSFER;AC-0001;AC-0002;60000"), ("E506 #2", "TRANSFER;AC-0001;AC-0002;70000"),
                ("E507 in between", "TRANSFER;AC-0001;AC-0002;2000"), ("E506 #3 (2 or 3 in a row?)", "TRANSFER;AC-0001;AC-0002;80000"),
                ("locked if E507 does not reset the streak", "TRANSFER;AC-0001;AC-0002;100")])
budget()
