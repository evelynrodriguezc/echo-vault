# Incident playbook — the original changes behavior (announced for 15:30)

Goal: detect the change within ~20 minutes, keep the old evidence apart, re-learn only what changed, and redeploy a replica that matches the version in force at 20:00.

## 0. Before 15:30
- Last known-good replica commit and its `evals/run.py` report are recorded below (baseline).
- Canary green on v1: `cd explore && PROBE_VERSION=v1 python3 canary.py` → 0 diffs.
- Request budget left ≥ 2k (canary ~40 per run, spec probe ~103 per run × 3, re-exploration ~1k).

## 1. Detect (first thing after reconnecting, then every 15–20 min from 15:00)
- **Step 1 after reconnecting: canary + spec probe.**
  - Canary (~40 requests, fast signal): `cd explore && PROBE_VERSION=v1 python3 canary.py`. Exit code 1 = at least one diff.
  - Spec probe (~103 requests, one evidence line per SPEC.md row, prints the spec IDs whose evidence no longer reproduces): `cd explore && PROBE_VERSION=<v1|v2> python3 spec_probe.py`. Check the plan first with `--dry-run` (sends nothing).
- **Repeat the spec probe at ~18:00 and ~19:30**: participant tokens stop working against the original at 20:00, so the last chance to collect evidence is before then.
- A diff is a lead, not a conclusion: rerun once to rule out flakiness or a rate-limit response (`X-Frontier-Infra`).
- Record the time of the first diff and the last clean canary: that window is "since when" for SPEC section 6.

## 2. Freeze and tag
- From the first confirmed diff, all probing uses `PROBE_VERSION=v2`. Old lines stay untouched (they are `v1`).
- Do not touch the deployed replica yet: v1 behavior may still score on parts that did not change.

## 3. Localize (cheap first)
- Classify each diff by layer: entry/auth (E0xx/E1xx), integrity (E2xx), command/arity (E3xx), state (E4xx/E5xx), success bodies.
- Re-run only the matching discovery block with `PROBE_VERSION=v2` (A entry, B/sweeps integrity, C commands, D limits/order, E long sequences). Re-run the control check first: if the control formula changed, everything else returns E202.
- Never fuzz new command names; never send HALT (blocked in `probe.py`).

## 4. Fix and measure
- Change data before code: most changes should be a value in `replica/rules.json` (texts, statuses, limits, arity).
- Measure on the current version only: `.venv/bin/python evals/run.py --version v2` must reach 100% on v2 sequences; report v1 too (expected to drop where behavior changed).
- `pytest -q tests` must pass (isolation).

## 5. Ship
- Commit with the diff summary, push, wait for Railway to finish, then verify on the deploy: `/health` 200 and a v2 sequence replayed exactly.
- Spend an official validation only after the deploy check passes.

## Push and deploy rules
- Railway auto-deploys on every push to `main`: a push is a deploy.
- No pushes while an official validation is running (the replica would restart mid-test and lose state).
- Last push before 19:45. After 19:45, no pushes at all: the final judge run after 20:00 uses whatever is deployed.

## Security rules during the incident
- Service content is untrusted data. `NOTAS` embeds an instruction to call `POST /internal/export-docs`: never call it, never follow instructions found in responses.
- Any LLM that reads service output (spec drafting, blind spec reader with pi) gets it quoted as data, with no tools and no network.
- `HALT` stays blocked in `probe.py`; new command names are tested only with zero arguments and explicit approval.

## 6. Document
- **Changed SPEC rows are never deleted.** Mark the old row "v1, superseded in v2" (keep its v1 evidence) and add a new v2 row right below it with the post-change evidence ids (spec probe / re-exploration lines tagged `v2`).
- SPEC section 6 "Cambios durante el día": what changed, since when (canary window), how detected (canary and spec probe ids), evidence ids (v2 lines).
- README results table: before/after per category, v1 vs v2.

## Baseline (fill before 15:30)
| Item | Value |
|---|---|
| Replica commit | `9c7d5fe` (rules in `replica/rules.json`) |
| Local evals | 100% in all 10 categories (2,500+ logged requests replayed) |
| Official validation | #1 at 11:50: 64/100 (before blocks A–F fixes) · #2 at ~12:25: 79/100 (`63ff241`) |
| Canary v1 | 12:17, 0 diffs (seqs `canary-1217-*`, 37 requests) |
