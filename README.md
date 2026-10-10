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

| Category | Sequences | Requests |
|---|---|---|
| Recorded examples | 1/1 | 21/21 |
| Discovery batches (entrada-auth, integridad, errores, comandos) | 31/31 | 950/950 |
| Hold-out v1 (random, 100 seqs) | 100/100 | 437/437 |
| Hold-out v2 (money flows, 30 seqs) — before same-holder rule | 28/30 | 379/388 |
| Hold-out v2 — after same-holder rule | 30/30 | 388/388 |

Honest finding: hold-out v1 was biased toward errors (100 of 437 responses were `E401`, only 13 successful deposits/transfers, 1 `E506`, no `E507`) because the generator often referenced accounts that did not exist yet. It passed 100% but under-tested money flows. Hold-out v2 fixed that and exposed a real rule we had missed: the transfer limit is skipped between accounts with the same holder name.

## Layout

- `replica/engine.py` — pure state machine `handle(state, m) -> (status, body)`.
- `replica/app.py` — HTTP layer (routing, auth, JSON parsing).
- `explore/` — prober and experiment batches (only these talk to the original).
- `evals/run.py` — offline replay of the experiment log against the replica.

## Deploy

Railway, single instance. Only `TEAM_TOKEN` is set as a variable. Start command from `Procfile`.
