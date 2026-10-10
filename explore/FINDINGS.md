# Findings (evidence index for SPEC.md)

## Control digit (integrity)
- Rule: `control = 98 - (100 * N mod 97)`, where N is the message without its last field, uppercased, letters mapped A=1..Z=26, digits kept, `;` and `-` dropped, concatenated as a base-10 number. Range 2–98. Implementation: `explore/control.py`.
- One valid value per message; checked before account existence: sweep of `CONSULTA;AC-0001` 0–99 (ids 310–410), only 14 accepted (325).
- Position weights (−3 per unit, −30 per ten, −9 ≡ −300 per hundred, wrap at 97): one-character sweeps, accepted values at ids 429 (AC-0000→17), 439 (AC-0003→8), 446 (AC-0004→5), 450 (AC-0005→2), 548 (AC-0006→96), 643 (AC-0007→93), 735 (AC-0008→90), 821 (AC-0010→84), 904 (AC-0011→81), 914 (AC-0100→8).
- Case-insensitive: `consulta`/`Consulta` → 14 (930, 946), same as `CONSULTA` (325).
- Held-out predictions (not used to fit), all accepted: 948 (`CONSULTA;AC-0042;85`), 949 (`CONSULTA;AC-0777;14`), 950 (`DEPOSITO;AC-0003;12345;41`).
- Edge: value 97, not 0 (`CONSULTA;AC-0038`): 0 rejected E202 (951), 97 accepted (952); `00` rejected E202 (953).
- Consistency: formula matches all 643 logged observations with own valid token (29 accepted, 614 rejected).
- PING does not validate the control: 0–99 all return pong (ids 210–309, seq `sweep-ping`).

## Control format (E201 vs E202)
- E201 `control mal formado` when the last field is not 1–2 plain digits: 3+ digits (955 `014`, 956 `0014`, 964 `114`), spaces (958, 959), sign (960, 961), letters (962, 973), decimal (965), non-numeric last field (967 `CONSULTA;AC-0001`).
- E202 `control inválido` when it is 1–2 digits but not the expected value, compared as text: `02` for expected 2 is rejected (957); 99 (966), 39 (972), 12 (975), 88 (977).
- Empty segment anywhere → E104 `segmento vacío` (963 trailing `;`, 978 empty command).
- Single field (no `;`) → E103 `falta control`, also for PING (968, 969).

## Error precedence (one message, several faults)
- E104/E103 (shape) → E201 (control format) → E202 (control value) → E301/E302 (command, arity) → E401… (state).
- Unknown command: valid control → E301 (971, 980); wrong control → E202 (972); malformed → E201 (973).
- Bad arity: valid control → E302 (974, 981); wrong control → E202 (975); malformed → E201 (976).
- Missing account + wrong control → E202 (977); with valid control → E401 (325).

## Unknown command suggestion
- `consulta ` (trailing space) → E301 with extra field `"sugerencia": "CONSULTA"` (979); exact names without near match give no `sugerencia` (971, 980). Matching rule (edit distance? trim?) still unknown.

## Commands (batch `cmd-*`, ids ~983–1032)
- ALTA: any name (duplicates, spaces, digits, 40 chars) → 201 `cuentaId` AC-000n sequential; new balance 0.
- Amounts: E303 `monto inválido` for 0, negative, decimal, leading zeros, non-numeric, 999999999999; checked before account existence (DEPOSITO;AC-0009;abc → E303).
- Failed operations and ANULA do not consume `OP-` ids.
- TRANSFER: same source and destination → E304; missing account → E401; E506 checked before E507.
- ANULA: reverses the effect (balance may go negative: deposit annulled after part was moved → −600); nonexistent op or account id → E402; second ANULA → 200 `{"ok": false, "motivo": "ya anulada"}`.

## Transfer limit and same holder (hold-out v2)
- Limit is per operation: > 100000 → E506 (100000 passes, two of 100000 in a row pass: 1011, 1012).
- **Not applied between accounts with the same holder name**: 29/29 large transfers between different names → E506; 3/3 between two accounts named "Beto" skip the limit: 1529, 1530 (→ E507, insufficient) and 1598 (100001 → OK). Confidence: probable (2 sequences). Name comparison case-sensitivity untested.

## Block A — HTTP entry layer (ids 1858–1931)
- Body size: raw body > 8192 bytes → 413 `E101 cuerpo demasiado grande` (8192 ok, 8193 fails: binary search 1914–1927); counts the whole raw body, not only `m` (padded short m → E101, 1928).
- Order: route (E404) → auth (E001) → E101 → E100 → E102: big body without token → 401 (1929); on unknown route → 404 (1930); big invalid JSON → 413 (1931).
- Body shapes: empty / truncated JSON → E100 (1870, 1881); null, array, string, number, `{"M":…}`, m null/array/bool, `{}` → E102 (1871–1877, 1882, 1883); extra keys ignored (1878); duplicate key, last wins (1879); whitespace around JSON ok (1880).
- Content-Type ignored: none, text/plain, form, `charset=latin1` all parse JSON (1885–1888).
- Routes are exact: `/msg/`, `/MSG`, `//msg`, `/msg/extra`, `/health/`, `HEAD /health` (empty body), `OPTIONS`, `GET /__reset`, `POST /health`, `PUT`/`DELETE /msg`, `GET /` → 404 E404 (1890–1902); query string ignored (`/msg?x=1` → pong, 1892).
- Auth: exactly `Bearer <token>`; trailing space tolerated (1907); `bearer`/`BEARER` (1904, 1905), double space (1906), `Token`, bare token, `Bearer` alone, `Basic` → 401 (1908, 1910–1913).

## Block B — integrity edge cases (ids 1932–1955)
- Non-ASCII letters are ignored by the control (not mapped): `ALTA;Lucía` accepts the control of `ALTA;Luca` (1933) and rejects that of `ALTA;Lucia` (1934); same for `ñ` (1935, 1936); emoji name accepted (1950).
- Only ASCII 0–9 count as digits: arabic-indic digit inside an id is ignored by the control (1948 E202 with the value that counted it); as control → E201 (1947).
- Tabs, newlines, punctuation, digits-only names are accepted by ALTA (1937, 1938, 1949, 1952). Fields are not trimmed: `CONSULTA; AC-0001` → E401 (1940).
- `,` or `|` instead of `;` → single field → E103 (1943, 1944); `;` and `;;` → E104 (1945, 1946).
- PING skips both control checks: `PING;XX`, `PING;123`, `PING;1 ` → pong (1954, 1955, 1942); `PING;` → E104 (1953).
- E301 `sugerencia` also for ` PING` (leading space, 1941) and `ALTA2` (1951). Working rule (probable): suggested when the command is at edit distance ≤ 1 from a known one.

## Block C — command variants (ids 1956–1985)
- E301 adds `"sugerencia": <command>` when the unknown command is at Levenshtein distance ≤ 2 from a known one: 29/29 observations fit (distance 1: 1957–1960, 1963, 1965, 1967, 1969–1973; distance 2: 1961, 1962, 1964, 1966, 1968, 1985 `AYUDA`→`ANULA`); none for distance ≥ 3 (`LISTA`, `BAJA`, `SALDO`, `SALDOS`… 1978–1984, 971). Tie-break between two commands at equal distance: assumed (list order PING, ALTA, CONSULTA, DEPOSITO, TRANSFER, ANULA).
- PING with arguments → E302 (1975, 1976).
- Candidate hidden commands RETIRO, SALDO, EXTRACTO, HISTORIAL, MOVIMIENTOS, BAJA, LISTA, AYUDA → all E301: no hidden command found among them (1978–1985).

## Block D — open assumptions (ids 1986–2084)
- Same-holder rule uses the exact name string: `Beto`/`BETO` (1990), `Beto`/`Beto ` (1995), `Lucía`/`Lucia` (2000) → E506; `Ana`/`Ana` → 150000 passes (2005). Confidence now confirmed (with 1529, 1530, 1598).
- Amount: positive integer without leading zeros, at most 9999999999 (2047 ok); 10000000000 → E303 (2044); binary search 2008–2047. Replica bound was 10^9 (wrong 10×): before fix `supuestos` 8/9 seqs, 77/99 requests; after 9/9, 99/99.
- TRANSFER error order: E303 → E304 → E401 → E506 (2050–2054).
- Ids are literal (no normalization): `ac-0001`, `AC-1`, `AC-00001`, `AC0001`, `AC-0001 ` → E401 (2058–2062); `op-0001`, `OP-1` → E402 (2064, 2065).
- No cumulative transfer limit: 5 × 100000 in a row pass (2079–2083).
