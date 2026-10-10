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
