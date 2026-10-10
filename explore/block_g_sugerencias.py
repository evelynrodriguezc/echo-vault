"""Block G: mine E301 suggestions to reveal hidden command names. Every probe name is sent with ZERO
arguments (NAME;control) so a real command stops at the arity check. Destructive-sounding words are excluded.
A suggestion outside the 6 known commands is only logged as a lead; it is never executed.
"""
from control import control
from probe import budget, probe, reset

KNOWN = {"PING", "ALTA", "CONSULTA", "DEPOSITO", "TRANSFER", "ANULA"}
EXCLUDED = {"CIERRE", "CIERRA", "CERRAR", "STOP", "RESET", "SHUTDOWN", "KILL", "BORRA", "BORRAR", "ELIMINA",
            "SUSPENDE", "BLOQUEO", "BLOQUEA", "APAGA", "APAGAR", "HALT", "EXIT", "QUIT", "PURGE", "WIPE", "DROP"}
NAMES = [
    "HALX", "HAL", "HOLT", "HELP", "INFO", "STAT", "STATUS", "LOG", "LOGS", "AUDIT", "VERS", "VERSION", "ECHO",
    "TIME", "HORA", "FECHA", "DEBUG", "ADMIN", "DUMP", "LIST", "TOTAL", "RESUMEN", "CUENTA", "CUENTAS", "PAGO",
    "PAGAR", "COBRO", "CARGO", "ABONO", "CREDITO", "DEBITO", "PRESTAMO", "INTERES", "TASA", "LIMITE", "REVERSA",
    "REVERSO", "DEVOLVER", "RETIRA", "RETIRAR", "GIRO", "SALDOS", "MOVS", "EXTRACT", "HIST", "TITULAR", "CLIENTE",
    "ABRIR", "NUEVA", "MODIFICA", "CAMBIO", "RENOMBRA", "COMISION", "CUOTA", "FONDOS", "TRASPASO", "ENVIO",
    "RECARGA", "QQQQ", "ZZZZ", "XYZW", "KJHG",
]


def run():
    seq = "G-sugerencias"
    reset(seq)
    leads = {}
    for name in NAMES:
        assert name not in EXCLUDED and name not in KNOWN
        body = name  # zero arguments: m = NAME;control
        e, _ = probe(seq, f"suggestion mining: '{name}' with zero args; a suggestion outside the known 6 is a lead",
                     {"m": f"{body};{control(body)}"})
        r = e["response"]
        sug = r.get("sugerencia") if isinstance(r, dict) else None
        tag = ""
        if not (isinstance(r, dict) and r.get("error") == "E301"):
            tag = "  <-- NOT E301 (name may be a real command)"
            leads[name] = r
        elif sug and sug not in KNOWN:
            tag = "  <-- LEAD: unknown suggested command"
            leads[name] = r
        print(f"  {e['id']:>5} {name:10} -> {e['status']} {r}{tag}")
    print("LEADS:", leads)
    budget()


if __name__ == "__main__":
    run()
