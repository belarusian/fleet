# TICKET-002: health.py — Missing gate-log reference makes health metrics incomplete

## Title
Health-metric extraction does not incorporate the gate log (cycle-gate decisions), so "last gate outcome" is always `None` or stale.

## Evidence
`fleet/health.py` — the metric-extraction function (e.g. `extract_health_metrics()`) reads trajectory files and, in some cases, a `last_cycle.json` or similar summary. However, the gate log (the file that records pass/fail/skip decisions per cycle, e.g. `gate.log` or `gates.jsonl`) is never opened or parsed. The derived fields `last_gate_outcome` and `gate_streak` are either:
- Hard-coded to `None`
- Derived from a field that is never written by the gate runner

This means the health report cannot answer "did the last cycle pass its quality gate?"

## Impact
- Operators see a health snapshot with `last_gate_outcome: null` on every cycle and cannot detect a regression where the gate started failing.
- The "days since last successful gate" metric (if present) is always `∞` or `0`, making alerting rules for gate-regression useless.
- The health report gives a false sense of completeness: it reports trajectory counts and timing but omits the single most important quality signal.

## Suggestion
1. Add a `read_gate_log(path) -> list[GateRecord]` helper in `fleet/health.py` (or a new `fleet/gate_log.py`) that parses the gate log format.
2. Wire it into `extract_health_metrics()` so that `last_gate_outcome`, `gate_streak`, and `days_since_last_pass` are populated.
3. If the gate log file is absent, emit a `WARNING` and set the fields to `"unknown"` (not `None`) so the report distinguishes "no data" from "gate passed."
4. Add tests: `test_health_includes_gate_outcome`, `test_health_gate_log_missing_warns`.
