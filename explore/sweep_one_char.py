"""One-character control sweep: find the single accepted control for messages that differ by one character."""
from probe import budget, probe, reset

BODIES = [f"CONSULTA;AC-000{d}" for d in "0345678"] + [
    "CONSULTA;AC-0010", "CONSULTA;AC-0011", "CONSULTA;AC-0100",
    "consulta;AC-0001", "Consulta;AC-0001",
]


def find_control(seq, body):
    """Return the first control value that is not rejected as E202 (stops early to save budget)."""
    reset(seq)
    for v in range(100):
        entry, _ = probe(seq, f"one-char sweep: valid control for '{body}' (stop at first non-E202), trying {v}",
                         {"m": f"{body};{v}"})
        resp = entry["response"]
        if not (isinstance(resp, dict) and resp.get("error") == "E202"):
            return v, entry["status"], resp
    return None, None, None


results = {}
for i, body in enumerate(BODIES):
    v, status, resp = find_control(f"sweep1c-{i:02d}", body)
    results[body] = v
    print(f"{body:22} control={v} -> {status} {resp}")
budget()
