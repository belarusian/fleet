# TICKET-035 — Integration robustness: mixed root through discover→assess→render

**Phase:** Cycle 8 synthesis audit
**Status:** RESOLVED (test added)

## Problem
A scan root mixing a healthy project, a corrupt-JSON project, and a gate-only
project was not exercised end-to-end. The full pipeline
(discover → assess → render_portfolio) must render every row without crashing,
and each project must be classified correctly.

## Evidence
- Probed a mixed root: `healthy` (3 trajectories, active), `corrupt` (one
  corrupt + one good trajectory → only the good parses, active), `gateonly`
  (a red-gate cycle block, no trajectories → dead, outcome `gate:red`).
- `render_portfolio` rendered all three rows; the corrupt project's good file
  still produced a valid row; the gate-only project's outcome was derived from
  the gate log.

## Impact
Without this test, a regression that dropped a row, crashed on the corrupt
project, or mis-derived the gate-only outcome would go undetected at the
pipeline level (the individual edge cases are covered separately in
`test_robustness.py`).

## Suggestion
Add `test_integration_mixed_root_pipeline` to `tests/test_integration.py`.

## Tests
- Added: `test_integration_mixed_root_pipeline` in `tests/test_integration.py`.
