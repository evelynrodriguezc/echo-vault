"""Block K8 (v2): state transitions and scale. Looks for rules where an earlier request changes a later response.
Usage (from explore/): PROBE_VERSION=v2 PROBE_MAX=200 python3 block_k8_state.py K8a [K8b ...]
Responses are compared with the replica afterwards by `evals/run.py --version v2 -v`.
"""
import sys
import time

from control import control
from probe import budget, probe, reset


def ok(body):
    return {"m": f"{body};{control(body)}"}


def wrong(body, k=1):
    return {"m": f"{body};{(control(body) + k) % 97}"}


def run(seq, steps):
    reset(seq)
    for step in steps:
        if step == "PAUSE":
            time.sleep(2.5)
            continue
        hyp, req = step
        e, _ = probe(seq, f"v2 state check: {hyp}", req)
        print(f"  {e['id']:>5} {seq:16} {hyp[:46]:46} -> {e['status']} {str(e['response'])[:80]}")


SETUP = [("setup", ok("ALTA;Ana")), ("setup", ok("ALTA;Beto")), ("setup", ok("DEPOSITO;AC-0001;300000"))]
CHECK = [("balance AC-0001 after", ok("CONSULTA;AC-0001")), ("balance AC-0002 after", ok("CONSULTA;AC-0002"))]


def k8a():
    cases = {
        "E201": ({"m": "DEPOSITO;AC-0001;100;1a"}, ok("DEPOSITO;AC-0001;100")),
        "E202": (wrong("DEPOSITO;AC-0001;100"), ok("DEPOSITO;AC-0001;100")),
        "E301": (ok("DEPOSIT;AC-0001;100"), ok("DEPOSITO;AC-0001;100")),
        "E302": (ok("DEPOSITO;AC-0001"), ok("DEPOSITO;AC-0001;100")),
        "E303": (ok("DEPOSITO;AC-0001;abc"), ok("DEPOSITO;AC-0001;100")),
        "E401": (ok("DEPOSITO;AC-0009;100"), ok("DEPOSITO;AC-0001;100")),
        "E506": (ok("TRANSFER;AC-0001;AC-0002;120000"), ok("TRANSFER;AC-0001;AC-0002;50000")),
        "E507": (ok("TRANSFER;AC-0002;AC-0001;5"), ok("TRANSFER;AC-0001;AC-0002;5")),
    }
    for code, (bad, good) in cases.items():
        run(f"K8a-{code}", SETUP + [(f"error {code}", bad), (f"valid request right after {code}", good)] + CHECK)
    run("K8a-3errors", SETUP + [("E202 #1", wrong("DEPOSITO;AC-0001;100", 1)), ("E202 #2", wrong("DEPOSITO;AC-0001;100", 2)),
                                ("E202 #3", wrong("DEPOSITO;AC-0001;100", 3)), ("valid after 3 errors", ok("DEPOSITO;AC-0001;100")),
                                ("E506 #1", ok("TRANSFER;AC-0001;AC-0002;120000")), ("E506 #2", ok("TRANSFER;AC-0001;AC-0002;130000")),
                                ("E506 #3", ok("TRANSFER;AC-0001;AC-0002;140000")), ("valid transfer after 3 E506", ok("TRANSFER;AC-0001;AC-0002;1000"))] + CHECK)


def k8b():
    run("K8b-notas", SETUP + [("NOTAS fresh", ok("NOTAS")), ("deposit", ok("DEPOSITO;AC-0002;1000")), ("NOTAS after deposit", ok("NOTAS")),
                              ("E506", ok("TRANSFER;AC-0001;AC-0002;120000")), ("NOTAS after E506", ok("NOTAS")),
                              ("move out", ok("TRANSFER;AC-0001;AC-0002;100000")), ("annul deposit", ok("ANULA;OP-0001")),
                              ("NOTAS after ANULA / negative", ok("NOTAS")), ("E202", wrong("CONSULTA;AC-0001")),
                              ("E301", ok("SALDOS;AC-0001")), ("NOTAS after errors", ok("NOTAS"))] + CHECK)


def k8c():
    run("K8c-negative", SETUP + [
        ("move all out", ok("TRANSFER;AC-0001;AC-0002;100000")), ("annul funding deposit", ok("ANULA;OP-0001")),
        ("AC-0001 negative", ok("CONSULTA;AC-0001")), ("transfer INTO negative account", ok("TRANSFER;AC-0002;AC-0001;500")),
        ("balance", ok("CONSULTA;AC-0001")), ("deposit back to positive", ok("DEPOSITO;AC-0001;200000")),
        ("transfer from recovered account", ok("TRANSFER;AC-0001;AC-0002;1000")), ("annul the recovery deposit", ok("ANULA;OP-0004")),
        ("balance negative again", ok("CONSULTA;AC-0001")), ("deposit into negative", ok("DEPOSITO;AC-0001;1")),
        ("transfer exact balance of AC-0002", ok("CONSULTA;AC-0002"))] + CHECK)


def k8d():
    run("K8d-repeat", SETUP + [
        ("deposit", ok("DEPOSITO;AC-0001;777")), "PAUSE", ("same deposit after 2.5 s", ok("DEPOSITO;AC-0001;777")),
        ("transfer", ok("TRANSFER;AC-0001;AC-0002;333")), "PAUSE", ("same transfer after 2.5 s", ok("TRANSFER;AC-0001;AC-0002;333")),
        ("ALTA Carla", ok("ALTA;Carla")), "PAUSE", ("same ALTA after 2.5 s", ok("ALTA;Carla"))] + CHECK)


def k8e():
    names = ["Ana", "Beto", "Carla", "Diego", "Elena"]
    run("K8e-accounts", [(f"ALTA #{i + 1}", ok(f"ALTA;{names[i % 5]}")) for i in range(25)] + [
        ("consult AC-0025", ok("CONSULTA;AC-0025")), ("fund AC-0020", ok("DEPOSITO;AC-0020;5000")),
        ("transfer AC-0020 -> AC-0025", ok("TRANSFER;AC-0020;AC-0025;100")), ("consult AC-0025", ok("CONSULTA;AC-0025")),
        ("consult AC-0026 (missing)", ok("CONSULTA;AC-0026"))])


def k8f():
    run("K8f-ops", [("setup", ok("ALTA;Ana"))] + [(f"deposit #{i + 1}", ok(f"DEPOSITO;AC-0001;{i + 1}")) for i in range(30)] + [
        ("annul oldest OP-0001", ok("ANULA;OP-0001")), ("annul newest OP-0030", ok("ANULA;OP-0030")),
        ("annul middle OP-0015", ok("ANULA;OP-0015")), ("balance", ok("CONSULTA;AC-0001"))])


def k8g():
    run("K8g-huge", [("setup", ok("ALTA;Ana")), ("setup same holder", ok("ALTA;Ana"))] + [
        x for i in range(5) for x in ((f"deposit max #{i + 1}", ok(f"DEPOSITO;AC-0001;{9999999999 - i}")),
                                       (f"same-holder transfer max #{i + 1}", ok(f"TRANSFER;AC-0001;AC-0002;{9999999999 - i}")))
    ] + [("huge balance", ok("CONSULTA;AC-0002")), ("transfer huge back", ok("TRANSFER;AC-0002;AC-0001;9999999999"))])


BLOCKS = {"K8a": k8a, "K8b": k8b, "K8c": k8c, "K8d": k8d, "K8e": k8e, "K8f": k8f, "K8g": k8g}
if __name__ == "__main__":
    for name in sys.argv[1:] or BLOCKS:
        print(f"== {name}")
        BLOCKS[name]()
    budget()
