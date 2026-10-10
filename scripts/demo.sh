#!/usr/bin/env bash
# 2-minute demo against OUR deployed replica (never the original service).
# Usage: TEAM_TOKEN=... scripts/demo.sh        Optional: DEMO_URL=... DEMO_PAUSE=2
# Do not run it while an official validation is in progress: it resets the replica's state.
set -euo pipefail
cd "$(dirname "$0")/.."

URL="${DEMO_URL:-https://echo-vault.up.railway.app}"
PAUSE="${DEMO_PAUSE:-2}"
: "${TEAM_TOKEN:?set TEAM_TOKEN in the environment (it is never printed)}"
case "$URL" in
  *caja-negra*) echo "Refusing to run: DEMO_URL points to the original service." >&2; exit 1 ;;
esac

B=$'\e[1m'; DIM=$'\e[2m'; CYAN=$'\e[36m'; GREEN=$'\e[32m'; RED=$'\e[31m'; YELLOW=$'\e[33m'; R=$'\e[0m'

step() { printf '\n%s%s━━━  %s  ━━━%s\n' "$B" "$CYAN" "$1" "$R"; }
note() { printf '%s%s%s\n' "$DIM" "$1" "$R"; }
pause() { sleep "$PAUSE"; }

# call METHOD PATH [JSON_BODY] — prints the request (token masked) and the response, pretty.
call() {
  local method="$1" path="$2" body="${3:-}" out status
  printf '%s> %s %s%s' "$B" "$method" "$path" "$R"
  [ -n "$body" ] && printf '  %s' "$body"
  printf '   %sAuthorization: Bearer ••••%s\n' "$DIM" "$R"
  if [ -n "$body" ]; then
    out=$(curl -s -w '\n%{http_code}' -X "$method" -H "Authorization: Bearer $TEAM_TOKEN" \
      -H 'Content-Type: application/json' -d "$body" "$URL$path")
  else
    out=$(curl -s -w '\n%{http_code}' -X "$method" -H "Authorization: Bearer $TEAM_TOKEN" "$URL$path")
  fi
  status=$(tail -n1 <<<"$out")
  local color=$GREEN; [ "${status:0:1}" != "2" ] && color=$RED
  printf '%s%s< %s%s  ' "$B" "$color" "$status" "$R"
  sed '$d' <<<"$out" | python3 -c 'import json,sys; print(json.dumps(json.load(sys.stdin), ensure_ascii=False))' 2>/dev/null \
    || sed '$d' <<<"$out"
}

control() { python3 -c 'import sys; sys.path.insert(0, "explore"); from control import control; print(control(sys.argv[1]))' "$1"; }

printf '\n%s%secho-vault%s — exact replica of an undocumented service, rebuilt from black-box experiments\n' "$B" "$YELLOW" "$R"
note "target: $URL  (our deploy, not the original)"
pause

step "1. Health and a clean state"
call GET /health
call POST /__reset
pause

BODY="ALTA;Lucia"
CTL=$(control "$BODY")
WRONG=$(( CTL % 97 + 1 ))
step "2. Open an account — control digit computed with our formula"
note "control = 98 − (100·N mod 97), N = $BODY uppercased, A=1…Z=26, separators dropped  →  $CTL"
call POST /msg "{\"m\":\"$BODY;$CTL\"}"
pause

step "2b. Deposit and read the balance — v2 returns it as a string with 2 decimals"
note "since the 15:30 change (v2): 12345 is shown as \"123.45\""
call POST /msg "{\"m\":\"DEPOSITO;AC-0001;12345;$(control 'DEPOSITO;AC-0001;12345')\"}"
call POST /msg "{\"m\":\"CONSULTA;AC-0001;$(control 'CONSULTA;AC-0001')\"}"
pause

step "3. Same message, wrong control"
note "integrity check runs before the command: wrong value → E202"
call POST /msg "{\"m\":\"$BODY;$WRONG\"}"
pause

step "4. NOTAS — a hidden command we found through E301 suggestions"
note "its note embeds an instruction to call an internal endpoint: we return it as data and never act on it"
call POST /msg "{\"m\":\"NOTAS;$(control NOTAS)\"}"
pause

step "5. Offline evals: every logged v2 experiment replayed against the replica"
.venv/bin/python evals/run.py --version v2 2>/dev/null | grep -v "^TEAM_TOKEN set"
pause

step "Done"
note "spec: SPEC.md · experiment log: experimentos.jsonl · playbook: incident.md"
