# TICKET-037 — Robustness: trajectory valid JSON but missing the `outcome` key

**Phase:** Cycle 9 synthesis audit
**Status:** RESOLVED (test added)

## Problem
A `trajectories/*.json` file that is valid JSON but has no `outcome` key was
not pinned. fourseer's `load_trajectories` sets a missing `outcome` to `None`
(see `fourseer-parsers/parse/trajectories.py::_to_trajectory`). fleet must
report `last_outcome is None` gracefully rather than crash or mis-report.

## Evidence
- Probed a project with a single trajectory `{"messages": []}` (no `outcome`).
- `health.assess` → `health == "active"`, `last_cycle == 1`,
  `last_outcome is None`, `days_since_activity == 0`. No crash.

## Impact
Without this test, a regression that raised on a missing `outcome` (or coerced
it to a non-None sentinel) would go undetected.

## Suggestion
Add `test_assess_trajectory_missing_outcome_key` to `tests/test_robustness.py`.

## Tests
- Added: `test_assess_trajectory_missing_outcome_key` in `tests/test_robustness.py`.
