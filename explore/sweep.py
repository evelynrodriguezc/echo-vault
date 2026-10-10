"""Sweep control values 0..99 for a message body to find which ones the service accepts."""
import sys

from probe import budget, probe, reset


def sweep(seq, body, values=range(100)):
    reset(seq)
    accepted, others = [], {}
    for v in values:
        entry, _ = probe(seq, f"control sweep: which control values does '{body}' accept? trying {v}", {"m": f"{body};{v}"})
        err = entry["response"].get("error") if isinstance(entry["response"], dict) else None
        if err == "E202":
            continue
        if err in (None,) or entry["status"] < 400:
            accepted.append(v)
        else:
            others.setdefault(err, []).append(v)
    return accepted, others


if __name__ == "__main__":
    body = sys.argv[1]
    seq = sys.argv[2]
    acc, oth = sweep(seq, body)
    print(f"{body!r}: accepted={acc} other_errors={oth}")
    budget()
