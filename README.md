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

## Layout

- `replica/engine.py` — pure state machine `handle(state, m) -> (status, body)`.
- `replica/app.py` — HTTP layer (routing, auth, JSON parsing).
- `explore/` — prober and experiment batches (only these talk to the original).
- `evals/run.py` — offline replay of the experiment log against the replica.

## Deploy

Railway, single instance. Only `TEAM_TOKEN` is set as a variable. Start command from `Procfile`.
