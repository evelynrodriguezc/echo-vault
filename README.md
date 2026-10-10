# echo-vault

Exact replica of an undocumented account service, rebuilt from black-box experiments.
Design: [`DESIGN.md`](DESIGN.md) · Evidence index: [`explore/FINDINGS.md`](explore/FINDINGS.md) · Experiment log: [`experimentos.jsonl`](experimentos.jsonl)

## Run the replica

```bash
uv venv .venv && uv pip install --python .venv/bin/python -r requirements.txt httpx pytest
TEAM_TOKEN=<team token> .venv/bin/uvicorn --app-dir replica app:app --port 8000
```

Contract: `GET /health`, `POST /__reset`, `POST /msg` with `{"m": "CMD;args;control"}`, all with `Authorization: Bearer <TEAM_TOKEN>`. Any other route answers like the original (`404 E404`).

## Evaluate

```bash
.venv/bin/python evals/run.py      # replays every logged sequence + the 20 examples, per-category exact match
.venv/bin/python -m pytest -q tests  # isolation: replica never references the original service
```

## Results (offline replay, `evals/run.py`)

| Category                                                        | Sequences | Requests |
| --------------------------------------------------------------- | --------- | -------- |
| Recorded examples                                               | 1/1       | 21/21    |
| Discovery batches (entrada-auth, integridad, errores, comandos) | 31/31     | 950/950  |
| Hold-out v1 (random, 100 seqs)                                  | 100/100   | 437/437  |
| Hold-out v2 (money flows, 30 seqs) — before same-holder rule    | 28/30     | 379/388  |
| Hold-out v2 — after same-holder rule                            | 30/30     | 388/388  |

Official hidden set (100 tests, 3 runs allowed):

| Run | Time | Replica | Passing |
|---|---|---|---|
| 1 | 11:50 | `0da9042` (commands + same-holder rule) | 64/100 |
| 2 | ~12:25 | `63ff241` (+ blocks A–F: body limit E101, PING skips control, ASCII-only control digits, suggestion at distance ≤ 2, amount ≤ 9999999999, TRACE/non-standard methods) | 79/100 |
| 3 | reserved for after the 15:30 change | | |

Local evals stayed at 100% while the official score was 64 and 79: our hold-outs share the replica's blind spots, so the gap measures coverage, not code.

Honest finding: hold-out v1 was biased toward errors (100 of 437 responses were `E401`, only 13 successful deposits/transfers, 1 `E506`, no `E507`) because the generator often referenced accounts that did not exist yet. It passed 100% but under-tested money flows. Hold-out v2 fixed that and exposed a real rule we had missed: the transfer limit is skipped between accounts with the same holder name.

## Log completeness

Every request we sent to the original is in `experimentos.jsonl`, except these 3 (around 10:50, before the prober became the only network path):

1. `POST /msg` with raw body `{"m":"HALT;x;1"}` — a faulty test of our own HALT guard let it through; response not recorded. HALT is now blocked in `explore/probe.py` and was never sent again.
2. `GET /health` — check that the service was still up after (1): `200 {"ok":true}`.
3. `POST /msg` `{"m":"PING;1"}` — same check: `200 {"pong":true}`, `X-Req: 293`.

Since then `_send` is private and only `probe()` calls it, so every request is logged. Other notes: ids 1–82 were sent with a wrong token (all `401 E001`) and are excluded from evals; lines from id 1858 carry a `version` tag (`v1` = before the announced 15:30 change), untagged lines are `v1`.

## Known deviations

- `GET /health` returns `200 {"ok":true}` without a token only when `Host` is `healthcheck.railway.app` (Railway's healthcheck sends no token). Any other host gets `401 E001` like the original. Low risk: the hidden set is unlikely to spoof `Host`.

## Layout

- `replica/engine.py` — pure state machine `handle(state, m) -> (status, body)`.
- `replica/app.py` — HTTP layer (routing, auth, JSON parsing).
- `explore/` — prober and experiment batches (only these talk to the original).
- `evals/run.py` — offline replay of the experiment log against the replica.

## Deploy

Railway, single instance. Only `TEAM_TOKEN` is set as a variable. Start command and healthcheck (`/health`) in `railway.json`.
