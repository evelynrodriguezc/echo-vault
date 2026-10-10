"""Pure replica of the service behavior: handle(state, m) -> (status, body).

Evaluation order (see explore/FINDINGS.md): shape (E103/E104) -> control format (E201)
-> control value (E202) -> command / arity (E301/E302) -> arguments (E303/E304) -> state (E401...).
"""
import re

MAX_TRANSFER = 100_000
MAX_AMOUNT = 10**9  # assumed: 999999999999 is rejected, 500000 accepted; exact bound not probed yet

ARITY = {"PING": 0, "ALTA": 1, "CONSULTA": 1, "DEPOSITO": 2, "TRANSFER": 3, "ANULA": 1}


def err(status, code, mensaje, **extra):
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
    """Levenshtein distance (assumed rule for E301 'sugerencia': distance <= 1)."""
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
    return value if value < MAX_AMOUNT else None


def handle(state, m):
    if ";" not in m:
        return err(400, "E103", "falta control")
    fields = m.split(";")
    if any(f == "" for f in fields):
        return err(400, "E104", "segmento vacío")
    body, ctl = m.rsplit(";", 1)
    cmd, args = fields[0].upper(), fields[1:-1]
    if cmd != "PING":  # PING skips both control checks (PING;XX -> pong)
        if not re.fullmatch(r"[0-9]{1,2}", ctl):
            return err(400, "E201", "control mal formado")
        if ctl != str(control(body)):
            return err(400, "E202", "control inválido")
    if cmd not in ARITY:
        near = [c for c in ARITY if distance(cmd, c) <= 1]
        extra = {"sugerencia": near[0]} if near else {}
        return err(400, "E301", "comando desconocido ", **extra)
    if len(args) != ARITY[cmd]:
        return err(400, "E302", "aridad inválida")
    return COMMANDS[cmd](state, *args)


def cmd_ping(state):
    return 200, {"pong": True}


def cmd_alta(state, name):
    return 201, {"cuentaId": state.new_account(name)}


def cmd_consulta(state, acc):
    if acc not in state.accounts:
        return err(404, "E401", "cuenta inexistente")
    return 200, {"cuenta_id": acc, "saldo": state.accounts[acc]}


def cmd_deposito(state, acc, amount_text):
    amount = parse_amount(amount_text)
    if amount is None:
        return err(400, "E303", "monto inválido")
    if acc not in state.accounts:
        return err(404, "E401", "cuenta inexistente")
    state.accounts[acc] += amount
    return 200, {"status": "recieved", "operacionId": state.new_op("DEPOSITO", None, acc, amount)}


def cmd_transfer(state, src, dst, amount_text):
    amount = parse_amount(amount_text)
    if amount is None:
        return err(400, "E303", "monto inválido")
    if src == dst:
        return err(400, "E304", "origen y destino iguales")
    if src not in state.accounts or dst not in state.accounts:
        return err(404, "E401", "cuenta inexistente")
    same_holder = state.names[src] == state.names[dst]  # limit is skipped between accounts of one holder
    if amount > MAX_TRANSFER and not same_holder:
        return err(422, "E506", "límite excedido")
    if state.accounts[src] < amount:
        return err(422, "E507", "saldo insuficiente")
    state.accounts[src] -= amount
    state.accounts[dst] += amount
    return 200, {"status": "recieved", "operacionId": state.new_op("TRANSFER", src, dst, amount)}


def cmd_anula(state, op_id):
    op = state.ops.get(op_id)
    if op is None:
        return err(404, "E402", "operación inexistente")
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
