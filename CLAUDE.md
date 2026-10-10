# Frontier Hackathon BOG/26

Event context, rubric and budget in `NOTAS.md` (local, not committed).

## Scope
- Work only inside this repo. Don't pull context from other directories.
- Secrets live in `.env` (gitignored). Never print or commit `OPENROUTER_API_KEY`.

## Workflow
- Design before code: decisions and trade-offs in `DESIGN.md`, diagram included.
- Evals from day one: local set in `evals/`, one command to run it. Report per-category results before and after each meaningful change.
- Small changes with an explicit definition of done. Don't touch files outside the task's scope.
- Run tests/evals before every commit. Small commits, imperative messages, no `Co-Authored-By`.
- Prefer the simple solution. If there's a reasonable alternative, mention it in one line with its trade-off.
- Log cost and latency per agent run (limited budget, see `NOTAS.md`).

## Deliverables
- Stable entrypoint documented in `README.md` (how to run, how to evaluate).
- Short demo video.

## Language
- Everything in the repo is in English: code, comments, docs, commit messages, file names, demo script and pitch.
- Chat with me in Spanish, short and direct.
