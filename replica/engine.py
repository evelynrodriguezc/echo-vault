"""Pure replica of the service behavior: handle(state, m) -> (status, body).

Evaluation order (see explore/FINDINGS.md): shape (E103/E104) -> control format (E201)
-> control value (E202) -> command / arity (E301/E302) -> arguments (E303/E304) -> state (E401...).
"""
import json
import re
from pathlib import Path

RULES = json.loads((Path(__file__).parent / "rules.json").read_text())  # error codes/texts, arity, limits
MAX_TRANSFER = RULES["limits"]["max_transfer"]
MAX_AMOUNT = RULES["limits"]["max_amount"]
MAX_SUGGEST = RULES["limits"]["suggestion_max_distance"]

ARITY = RULES["arity"]  # order matters: tie-break for E301 suggestions


def err(code, **extra):
    status, mensaje = RULES["errors"][code]
    return status, {"error": code, "mensaje": mensaje, **extra}


def to_digits(body):
    digits = ""
    for ch in body.upper():
        if "0" <= ch <= "9":  # ASCII only: unicode digits are ignored like other symbols
            digits += ch
        elif "A" <= ch <= "Z":
            digits += str(ord(ch) - 64)
    return digits or "0"


def control(body):
    r = 0
    for d in to_digits(body):  # streaming mod 97: no big integers, any message length
        r = (r * 10 + int(d)) % 97
    return 98 - (100 * r) % 97


class State:
    def __init__(self):
        self.accounts = {}  # id -> balance
        self.names = {}  # id -> holder name given in ALTA
        self.ops = {}  # id -> {"kind", "src", "dst", "amount", "annulled"}

    def new_account(self, name):
        acc = f"AC-{len(self.accounts) + 1:04d}"
        self.accounts[acc] = 0
        self.names[acc] = name
        return acc

    def new_op(self, kind, src, dst, amount):
        op = f"OP-{len(self.ops) + 1:04d}"
        self.ops[op] = {"kind": kind, "src": src, "dst": dst, "amount": amount, "annulled": False}
        return op


def distance(a, b):
    """Levenshtein distance; E301 adds 'sugerencia' with the nearest command at distance <= 2."""
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


def parse_amount(text):
    if not re.fullmatch(r"[1-9][0-9]*", text):
        return None
    value = int(text)
    return value if value <= MAX_AMOUNT else None


def handle(state, m):
    if ";" not in m:
        return err("E103")
    fields = m.split(";")
    if any(f == "" for f in fields):
        return err("E104")
    body, ctl = m.rsplit(";", 1)
    cmd, args = fields[0].upper(), fields[1:-1]
    if cmd != "PING":  # PING skips both control checks (PING;XX -> pong)
        if not re.fullmatch(r"[0-9]{1,2}", ctl):
            return err("E201")
        if ctl != str(control(body)):
            return err("E202")
    if cmd not in ARITY:
        candidates = list(ARITY) + RULES["suggest_only"]  # hidden commands seen only through suggestions
        near = sorted((distance(cmd, c), i, c) for i, c in enumerate(candidates) if distance(cmd, c) <= MAX_SUGGEST)
        extra = {"sugerencia": near[0][2]} if near else {}
        return err("E301", **extra)
    if len(args) != ARITY[cmd]:
        return err("E302")
    return COMMANDS[cmd](state, *args)


def cmd_ping(state):
    return 200, {"pong": True}


def cmd_alta(state, name):
    return 201, {"cuentaId": state.new_account(name)}


def cmd_consulta(state, acc):
    if acc not in state.accounts:
        return err("E401")
    return 200, {"cuenta_id": acc, "saldo": state.accounts[acc]}


def cmd_deposito(state, acc, amount_text):
    amount = parse_amount(amount_text)
    if amount is None:
        return err("E303")
    if acc not in state.accounts:
        return err("E401")
    state.accounts[acc] += amount
    return 200, {"status": "recieved", "operacionId": state.new_op("DEPOSITO", None, acc, amount)}


def cmd_transfer(state, src, dst, amount_text):
    amount = parse_amount(amount_text)
    if amount is None:
        return err("E303")
    if src == dst:
        return err("E304")
    if src not in state.accounts or dst not in state.accounts:
        return err("E401")
    same_holder = state.names[src] == state.names[dst]  # limit is skipped between accounts of one holder
    if amount > MAX_TRANSFER and not same_holder:
        return err("E506")
    if state.accounts[src] < amount:
        return err("E507")
    state.accounts[src] -= amount
    state.accounts[dst] += amount
    return 200, {"status": "recieved", "operacionId": state.new_op("TRANSFER", src, dst, amount)}


def cmd_anula(state, op_id):
    op = state.ops.get(op_id)
    if op is None:
        return err("E402")
    if op["annulled"]:
        return 200, {"ok": False, "motivo": "ya anulada"}
    op["annulled"] = True
    if op["src"]:
        state.accounts[op["src"]] += op["amount"]
    state.accounts[op["dst"]] -= op["amount"]
    return 200, {"ok": True, "anulada": op_id}


COMMANDS = {
    "PING": cmd_ping, "ALTA": cmd_alta, "CONSULTA": cmd_consulta,
    "DEPOSITO": cmd_deposito, "TRANSFER": cmd_transfer, "ANULA": cmd_anula,
}
