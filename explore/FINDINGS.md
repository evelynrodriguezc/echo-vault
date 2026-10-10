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
