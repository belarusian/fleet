# TICKET-031 — Robustness: empty gate log (present but empty) → empty GateLog → dead

**Phase:** Cycle 8 synthesis audit
**Status:** RESOLVED (test added)

## Problem
A project whose gate log file exists but is **empty** (zero bytes) was not
covered by a test. The behavior is correct but was unverified: an empty gate
log must parse to an empty `GateLog` (no cycle blocks, no build order), and
`assess` must classify the project as `dead` with all-`None` cycle metrics.

## Evidence
- `fourseer/parse/gate_log.py:parse_gate_log`: `text.splitlines()` on `""`
  yields `[]`; both `_parse_build_order` and `_parse_cycle_blocks` return `[]`.
- `fourseer/load.py:load_run`: `gate_text = ""` (not `None`), so
  `parse_gate_log("")` is called → `GateLog(build_order=[], cycles=[])`.
- `fleet/health.py:_gate_log_outcome`: `if not run.gate_log.cycles: return None`.
- Probed: `assess` on an empty gate log → `health="dead"`, `last_cycle=None`,
  `last_outcome=None`, `days_since_activity=0` (the empty file still has an
  mtime, so it contributes a recency signal).

## Impact
Without a test, a regression in `parse_gate_log` (e.g. raising on empty input)
or in `load_run`'s empty-vs-`None` gate-text handling would go undetected.

## Suggestion
Add `test_assess_empty_gate_log` to `tests/test_robustness.py`.

## Tests
- Added: `test_assess_empty_gate_log` in `tests/test_robustness.py`.
