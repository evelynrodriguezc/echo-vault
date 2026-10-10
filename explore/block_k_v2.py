"""Block K (after the 15:30 change, PROBE_VERSION=v2): re-check areas the canary and spec probe do not cover.
Every response is later compared with the replica (still v1) by `evals/run.py --version v2 -v`.
Known command names only; HALT only appears as the near-miss `HALX` with zero arguments.
"""
from control import control
from probe import TOKEN, budget, probe, reset


def ok(body):
    return {"m": f"{body};{control(body)}"}


def run(seq, steps):
    reset(seq)
    for step in steps:
        hyp, req = step[0], step[1]
        kw = step[2] if len(step) > 2 else {}
        e, _ = probe(seq, f"v2 check: {hyp}", req, **kw)
        print(f"  {e['id']:>5} {seq:14} {hyp[:44]:44} -> {e['status']} {str(e['response'])[:90]}")


SETUP2 = [("setup", ok("ALTA;Ana")), ("setup", ok("ALTA;Beto")), ("setup", ok("DEPOSITO;AC-0001;500000"))]

run("K1-limits", SETUP2 + [
    ("transfer 100000 different holders", ok("TRANSFER;AC-0001;AC-0002;100000")),
    ("transfer 100001 different holders", ok("TRANSFER;AC-0001;AC-0002;100001")),
    ("transfer 99999", ok("TRANSFER;AC-0001;AC-0002;99999")),
    ("deposit 9999999999", ok("DEPOSITO;AC-0002;9999999999")),
    ("deposit 10000000000", ok("DEPOSITO;AC-0002;10000000000")),
    ("transfer 10000000000", ok("TRANSFER;AC-0002;AC-0001;10000000000")),
    ("amount 0", ok("DEPOSITO;AC-0001;0")), ("amount -5", ok("DEPOSITO;AC-0001;-5")),
    ("amount 007", ok("DEPOSITO;AC-0001;007")), ("amount 1.5", ok("DEPOSITO;AC-0001;1.5")),
    ("amount 1", ok("DEPOSITO;AC-0001;1")),
    ("balance after", ok("CONSULTA;AC-0001")), ("balance after", ok("CONSULTA;AC-0002")),
])
run("K1-holder", [("setup", ok("ALTA;Ana")), ("setup", ok("ALTA;Ana")), ("setup", ok("ALTA;ANA")),
                  ("setup", ok("DEPOSITO;AC-0001;500000")),
                  ("same holder 150000", ok("TRANSFER;AC-0001;AC-0002;150000")),
                  ("Ana -> ANA 150000", ok("TRANSFER;AC-0001;AC-0003;150000")),
                  ("same holder 100001", ok("TRANSFER;AC-0001;AC-0002;100001"))])
big = "X" * 8175
run("K1-body", [("body 8192 bytes", ok("ALTA;" + big)), ("body 8193 bytes", ok("ALTA;" + big + "X")),
                ("big body without token", None, {"raw_body": '{"m":"PING;1"}' + " " * 9000, "token": None})])

run("K2-errors", [
    ("E103", {"m": "CONSULTA"}), ("E104", {"m": "CONSULTA;AC-0001;"}), ("E201", {"m": "CONSULTA;AC-0001;1a"}),
    ("E202", {"m": "CONSULTA;AC-0001;15"}), ("E301", ok("SALDOS;AC-0001")), ("E302", ok("CONSULTA")),
    ("E303", ok("DEPOSITO;AC-0001;abc")), ("E304", ok("TRANSFER;AC-0001;AC-0001;10")),
    ("E401", ok("CONSULTA;AC-0009")), ("E402", ok("ANULA;OP-0099")),
    ("E100", None, {"raw_body": "hola"}), ("E102", None, {"raw_body": '{"x":1}'}),
    ("E404", None, {"method": "GET", "path": "/nope"}), ("E001", {"m": "PING;1"}, {"token": None}),
    ("E506 setup", ok("ALTA;Ana")), ("E506 setup", ok("ALTA;Beto")), ("E506 setup", ok("DEPOSITO;AC-0001;300000")),
    ("E506", ok("TRANSFER;AC-0001;AC-0002;120000")), ("E507", ok("TRANSFER;AC-0002;AC-0001;5")),
    ("health", None, {"method": "GET", "path": "/health"}),
])
run("K3-order", [
    ("unknown cmd + wrong control", {"m": "SALDOS;AC-0001;39"}), ("unknown cmd + malformed", {"m": "SALDOS;AC-0001;5X"}),
    ("arity + wrong control", {"m": "ALTA;Lucia;Gomez;12"}), ("arity + valid control", ok("ALTA;Lucia;Gomez")),
    ("missing acct + wrong control", {"m": "CONSULTA;AC-0009;88"}),
    ("E303 vs E304 vs E401", ok("TRANSFER;AC-0009;AC-0009;abc")), ("E304 vs E401", ok("TRANSFER;AC-0009;AC-0009;10")),
    ("E401 vs E506", ok("TRANSFER;AC-0001;AC-0009;100001")), ("E303 vs E401", ok("TRANSFER;AC-0009;AC-0001;abc")),
    ("empty field vs control", {"m": ";AC-0001;35"}), ("E101 vs E100", None, {"raw_body": '{"m":' + "x" * 9000}),
    ("E101 vs route", None, {"raw_body": '{"m":"PING;1"}' + " " * 9000, "path": "/nope"}),
])
run("K4-control", [
    ("02 for expected 2", {"m": "CONSULTA;AC-0005;02"}), ("edge 0", {"m": "CONSULTA;AC-0038;0"}),
    ("edge 97", {"m": "CONSULTA;AC-0038;97"}), ("accent ignored", {"m": "ALTA;Lucía;14"}),
    ("accent mapped", {"m": "ALTA;Lucía;82"}), ("unicode digit in id", {"m": "CONSULTA;AC-000١;14"}),
    ("PING;XX", {"m": "PING;XX"}), ("PING;123", {"m": "PING;123"}), ("NOTAS wrong control", {"m": "NOTAS;12"}),
    ("lowercase command", {"m": "consulta;AC-0001;14"}), ("leading zero 014", {"m": "CONSULTA;AC-0001;014"}),
    ("prediction AC-0042", {"m": "CONSULTA;AC-0042;85"}),
])
run("K5-suggest", [
    ("distance 1", ok("CONSULT;AC-0001")), ("distance 2", ok("CONSUL;AC-0001")), ("distance 2 AL", ok("AL;AC-0001")),
    ("distance 3 LISTA", ok("LISTA;AC-0001")), ("AYUDA -> ANULA", ok("AYUDA;AC-0001")),
    ("HALX zero args", ok("HALX")), ("TOTAL zero args", ok("TOTAL")), ("leading space", {"m": " PING;64"}),
    ("ALTA2", ok("ALTA2;Ana")), ("SALDOS none", ok("SALDOS;AC-0001")),
])
run("K6-entry", [
    ("auth trailing space", {"m": "PING;1"}, {"auth_header": f"Bearer {TOKEN} "}),
    ("auth lowercase bearer", {"m": "PING;1"}, {"auth_header": f"bearer {TOKEN}"}),
    ("auth Token", {"m": "PING;1"}, {"auth_header": f"Token {TOKEN}"}),
    ("/msg/", {"m": "PING;1"}, {"path": "/msg/"}), ("/MSG", {"m": "PING;1"}, {"path": "/MSG"}),
    ("query string", {"m": "PING;1"}, {"path": "/msg?x=1"}), ("HEAD /health", None, {"method": "HEAD", "path": "/health"}),
    ("TRACE /msg", None, {"method": "TRACE", "path": "/msg"}), ("FOO /health", None, {"method": "FOO", "path": "/health"}),
    ("GET /msg", None, {"method": "GET", "path": "/msg"}), ("empty body", None, {"raw_body": ""}),
    ("JSON array", None, {"raw_body": "[]"}), ("m null", None, {"raw_body": '{"m":null}'}),
    ("m empty", {"m": ""}), ("extra key", None, {"raw_body": '{"m":"PING;1","x":1}'}),
    ("duplicate key", None, {"raw_body": '{"m":"x","m":"PING;1"}'}),
    ("text/plain", None, {"raw_body": '{"m":"PING;1"}', "content_type": "text/plain"}),
    ("reset without token", None, {"path": "/__reset", "token": None}),
    ("health without token", None, {"method": "GET", "path": "/health", "token": None}),
])
run("K7-state", [
    ("ALTA odd name", ok("ALTA;Ana Maria")), ("ALTA digits", ok("ALTA;123")), ("ALTA emoji", ok("ALTA;😀")),
    ("ALTA long", ok("ALTA;" + "Z" * 40)), ("new balance", ok("CONSULTA;AC-0004")),
    ("fund", ok("DEPOSITO;AC-0001;1000")), ("transfer 600", ok("TRANSFER;AC-0001;AC-0002;600")),
    ("spend it", ok("TRANSFER;AC-0002;AC-0003;600")), ("annul transfer spent", ok("ANULA;OP-0002")),
    ("negative dest", ok("CONSULTA;AC-0002")), ("annul chain", ok("ANULA;OP-0003")), ("annul deposit", ok("ANULA;OP-0001")),
    ("annul again", ok("ANULA;OP-0002")), ("annul missing", ok("ANULA;OP-0099")), ("annul account id", ok("ANULA;AC-0001")),
    ("op counter after annul", ok("DEPOSITO;AC-0001;5")), ("balance", ok("CONSULTA;AC-0001")),
    ("transfer from negative", ok("TRANSFER;AC-0002;AC-0001;1")), ("deposit into negative", ok("DEPOSITO;AC-0002;500")),
    ("balance", ok("CONSULTA;AC-0002")), ("NOTAS", ok("NOTAS")),
    ("5 transfers setup", ok("DEPOSITO;AC-0001;600000")),
] + [(f"transfer #{i + 1}", ok(f"TRANSFER;AC-0001;AC-0003;{100000 - i}")) for i in range(5)] + [
    ("balance after 5", ok("CONSULTA;AC-0001")), ("id format ac-0001", ok("CONSULTA;ac-0001")),
])
budget()
