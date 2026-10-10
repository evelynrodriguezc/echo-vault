# echo-vault

Exact replica of an undocumented account service, rebuilt from black-box experiments.
Design: [`DESIGN.md`](DESIGN.md) · Evidence index: [`explore/FINDINGS.md`](explore/FINDINGS.md) · Experiment log: [`experimentos.jsonl`](experimentos.jsonl)

## Engineering highlights

1. **Hidden set: 64 → 79 → pending (after incident), out of 100.** Our local evals were at 100% on both runs because they replay our own experiments, so they share the replica's blind spots. The gap measured coverage, not code; targeted exploration (blocks A–H) closed most of it. [Results](#results-offline-replay-evalsrunpy)
2. **Prompt injection in service data, detected and not followed.** The hidden command `NOTAS` returns a note asking the reader to call `POST /internal/export-docs` with their token. We replicate it verbatim as data, never called the endpoint, and run any LLM that reads service output with no tools or network. [Security findings](#security-findings) · log ids 2854–2857
3. **1 unsafe request, reported.** A faulty test of our own guard sent one `HALT` to the shared original (it stayed up). `HALT` is now blocked at the only network path, and the 3 requests that never reached the log are listed. [Log completeness](#log-completeness) · [`explore/probe.py`](explore/probe.py)
4. **Spec rebuilt blind: 99.97% for $0.04.** A model given only `SPEC.md` (no tools, no network) wrote a reimplementation that matches 2980 of 2981 logged requests; its first run exposed 3 spec gaps we then fixed. [Blind spec check](#blind-spec-check)
5. **Check digit found by sweep, confirmed by prediction.** Sweeping control values 0–99 on messages that differ by one character showed weights of −3 per unit mod 97, giving `98 − (100·N mod 97)`; it matches all 643 logged observations and predicted 3 unseen messages correctly. [Control digit evidence](explore/FINDINGS.md#control-digit-integrity) · log ids 948–953

## Run the replica

Requires [uv](https://docs.astral.sh/uv/) (it fetches Python ≥ 3.12 if needed). From the repo root:

```bash
uv venv .venv && uv pip install --python .venv/bin/python -r requirements.txt httpx pytest
TEAM_TOKEN=<team token> .venv/bin/uvicorn --app-dir replica app:app --port 8000
```

Smoke test from another terminal:

```bash
curl -H "Authorization: Bearer <team token>" localhost:8000/health                        # {"ok":true}
curl -H "Authorization: Bearer <team token>" -d '{"m":"PING;1"}' localhost:8000/msg       # {"pong":true}
```

Demo (used for the video; resets the deployed replica, so never during an official validation; refuses to target the original): `TEAM_TOKEN=<team token> scripts/demo.sh` (`DEMO_URL`, `DEMO_PAUSE` optional).

Contract: `GET /health`, `POST /__reset`, `POST /msg` with `{"m": "CMD;args;control"}`, all with `Authorization: Bearer <TEAM_TOKEN>`. Any other route answers like the original (`404 E404`).

## Evaluate

Offline, no network and no secrets needed:

```bash
.venv/bin/python evals/run.py        # replays every logged sequence against the replica, per-category exact match
.venv/bin/python -m pytest -q tests  # isolation: replica never references the original service
```

The challenge material (`material/`, with the 20 public examples) is not in the repo; the same 20 requests are in the log as sequences `recon2-replay-1/2`, so `evals/run.py` still covers them. Two scripts need more than the repo:

- `explore/*.py` (prober, canary, spec probe) talk to the original: a `.env` at the repo root with `BLACKBOX_URL` and `BLACKBOX_TOKEN` (participant tokens stop working at 20:00 on event day). Standard library only: `cd explore && python3 canary.py`.
- `evals/blind_reader.py` calls an LLM through [pi](https://pi.dev) with `OPENROUTER_API_KEY` set; `--reuse` re-evaluates the saved generated code without calling the model.

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

## Blind spec check

`evals/blind_reader.py` asks a model (pi + `anthropic/claude-sonnet-5.5`, no tools/network, SPEC.md passed as untrusted data) to reimplement the service from `SPEC.md` alone, then replays the whole experiment log against that code.

| Run | Spec version | Matching requests | Mismatches | Cost / latency |
|---|---|---|---|---|
| 1 | first SPEC.md | 2972/2981 (99.7%) | 9: 7 crashes on long messages (spec did not warn that N has thousands of digits), `FOO` method missing from the error order, `HEAD` body | $0.040 / 12.9 s |
| 2 | after fixing those gaps | 2980/2981 (99.97%) | 1: `HEAD /health` body — harness artifact (HTTP never sends a body for HEAD; the replica matches over real HTTP) | $0.042 / 13.7 s |

Generated code and mismatches: `evals/blind/`. Runs are logged in `evals/blind/runs.jsonl`.

## Log completeness

Every request we sent to the original is in `experimentos.jsonl`, except these 3 (around 10:50, before the prober became the only network path):

1. `POST /msg` with raw body `{"m":"HALT;x;1"}` — a faulty test of our own HALT guard let it through; response not recorded. HALT is now blocked in `explore/probe.py` and was never sent again.
2. `GET /health` — check that the service was still up after (1): `200 {"ok":true}`.
3. `POST /msg` `{"m":"PING;1"}` — same check: `200 {"pong":true}`, `X-Req: 293`.

Since then `_send` is private and only `probe()` calls it, so every request is logged. Other notes: ids 1–82 were sent with a wrong token (all `401 E001`) and are excluded from evals; lines from id 1858 carry a `version` tag (`v1` = before the announced 15:30 change), untagged lines are `v1`.

## Known deviations

- `GET /health` returns `200 {"ok":true}` without a token only when `Host` is `healthcheck.railway.app` (Railway's healthcheck sends no token). Any other host gets `401 E001` like the original. Low risk: the hidden set is unlikely to spoof `Host`.

## Security findings

- **Embedded instruction in service data (prompt-injection risk).** The hidden command `NOTAS` returns a note asking the reader to call `POST /internal/export-docs` with their token (log ids 2854–2857). We treat it as data: the replica returns it verbatim and never acts on it, and we never called that endpoint. A new client must not inherit this behavior (SPEC: Risks).
- **Rule for any LLM that reads service content** (e.g. the blind spec reader with pi): quote service responses as data inside clearly delimited blocks, state that they are untrusted, and run the model with no tools and no network (`pi --no-tools --no-extensions --no-mcp`), so the injected note cannot trigger actions.
- **`HALT`** exists (revealed by E301 suggestions) and may stop the shared service; it is blocked in `explore/probe.py` and never executed.

## Layout

- `replica/engine.py` — pure state machine `handle(state, m) -> (status, body)`.
- `replica/app.py` — HTTP layer (routing, auth, JSON parsing).
- `explore/` — prober and experiment batches (only these talk to the original).
- `evals/run.py` — offline replay of the experiment log against the replica.

## Deploy

Railway, single instance. Only `TEAM_TOKEN` is set as a variable. Start command and healthcheck (`/health`) in `railway.json`.
