"""Spec probe: re-check SPEC.md against the live original.

For each SPEC.md row, pick its cheapest evidence line(s) from experimentos.jsonl, resend the state-changing
lines before it (since its reset) and the line itself through probe() (logged, version tag from PROBE_VERSION),
and compare with the logged response. Prints the spec IDs whose evidence no longer reproduces.

Usage (from explore/):
    PROBE_VERSION=v2 PROBE_MAX=200 python3 spec_probe.py [--max 150] [--dry-run]
--dry-run prints the plan and its request count without sending anything.
"""
import json
import re
import sys
import time

from probe import ROOT, TOKEN, budget, probe, reset

MAX = int(sys.argv[sys.argv.index("--max") + 1]) if "--max" in sys.argv else 150
DRY = "--dry-run" in sys.argv
FIRST_VALID_ID = 83  # ids 1-82 were sent with a wrong token
PER_ROW = int(sys.argv[sys.argv.index("--per-row") + 1]) if "--per-row" in sys.argv else 1  # evidence lines per spec row


def spec_rows():
    """Return {spec_id: [log ids]} from the evidence column (second to last cell) of SPEC.md tables."""
    rows = {}
    for line in (ROOT / "SPEC.md").read_text().splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) < 3 or not re.fullmatch(r"[A-Z]+-[A-Za-z0-9]+", cells[0]):
            continue
        ids = set()
        for a, b in re.findall(r"\b(\d{3,4})(?:–(\d{3,4}))?\b", cells[-2]):
            ids.update(range(int(a), int(b or a) + 1))
        if ids:
            rows[cells[0]] = sorted(ids)
    return rows


def load_log():
    entries, seqs = {}, {}
    for line in (ROOT / "experimentos.jsonl").open():
        e = json.loads(line)
        if e["id"] < FIRST_VALID_ID or e.get("infra"):  # rate limits and client errors are not service behavior
            continue
        entries[e["id"]] = e
        seqs.setdefault(e["seq"], []).append(e)
    return entries, seqs


def changes_state(e):
    r = e["response"]
    return isinstance(r, dict) and ("cuentaId" in r or "operacionId" in r or bool(r.get("anulada")))


def plan(rows, entries, seqs):
    """Per row, pick the evidence line(s) with the fewest lines to send: the state-changing lines before it
    (since its sequence's last reset) plus the line itself. Errors and reads before it do not affect it."""
    position = {e["id"]: i for s in seqs.values() for i, e in enumerate(s)}

    def lines_for(i):
        s = seqs[entries[i]["seq"]]
        start = max([k for k in range(position[i]) if s[k]["path"] == "/__reset"], default=-1) + 1
        return [e for e in s[start:position[i]] if changes_state(e)] + [entries[i]]

    need, targets = {}, {}  # seq -> {log id: entry}; log id -> spec ids it checks
    for spec_id, ids in rows.items():
        usable = [i for i in ids if i in entries and entries[i]["path"] != "/__reset"]
        for i in sorted(usable, key=lambda i: len(lines_for(i)))[:PER_ROW]:
            need.setdefault(entries[i]["seq"], {}).update({e["id"]: e for e in lines_for(i)})
            targets.setdefault(i, []).append(spec_id)
    cost = sum(len(lines) + 1 for lines in need.values())  # + one reset per sequence
    return need, targets, cost


def resend(seq_name, e):
    kwargs = dict(method=e["method"], path=e["path"], content_type=e.get("content_type", "application/json"))
    auth = e.get("auth", "own")
    if auth == "custom":
        kwargs["auth_header"] = e["auth_header"].replace("<own>", TOKEN)
    elif auth == "none":
        kwargs["token"] = None
    elif auth == "other":
        kwargs["token"] = "wrong-token-123"
    req = e["request"]
    if isinstance(req, str):
        kwargs["raw_body"] = req
        req = None
    return probe(seq_name, f"spec probe: re-check logged line {e['id']} ({e['seq']})", req, **kwargs)[0]


def run():
    rows = spec_rows()
    entries, seqs = load_log()
    need, targets, cost = plan(rows, entries, seqs)
    print(f"spec rows with evidence: {len(rows)} | sequences to replay: {len(need)} | planned requests: {cost}")
    if cost > MAX:
        sys.exit(f"plan needs {cost} requests > --max {MAX}; lower PER_ROW or raise --max")
    if DRY:
        for seq, lines in sorted(need.items(), key=lambda kv: len(kv[1])):
            print(f"  {seq:28} send {len(lines)}: {sorted(lines)}")
        return
    stamp = time.strftime("%H%M")
    changed = {}
    for seq, lines in need.items():
        name = f"specprobe-{stamp}-{seq}"[:60]
        reset(name)
        for _, e in sorted(lines.items()):
            new = resend(name, e)
            if e["id"] in targets and (new["status"], new["response"]) != (e["status"], e["response"]):
                for spec_id in targets[e["id"]]:
                    changed.setdefault(spec_id, []).append(
                        (e["id"], new["id"], (e["status"], e["response"]), (new["status"], new["response"])))
    print(f"spec IDs whose evidence changed: {len(changed)} of {len(rows)}")
    for spec_id, diffs in sorted(changed.items()):
        for old_id, new_id, old, new in diffs:
            print(f"  {spec_id}: log {old_id} -> new {new_id}\n     was {old}\n     now {new}")
    budget()


if __name__ == "__main__":
    run()
