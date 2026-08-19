# TICKET-039 — Robustness: trajectory `outcome` is a non-string (number)

**Phase:** Cycle 9 synthesis audit
**Status:** RESOLVED (test added)

## Problem
A trajectory whose `outcome` is a non-string (e.g. the number `42`) was not
pinned. fourseer's `_to_trajectory` coerces a non-string `outcome` to `str`
(see `fourseer-parsers/parse/trajectories.py`). fleet must report the coerced
string (`"42"`) gracefully.

## Evidence
- Probed a project with a single trajectory `{"outcome": 42, "messages": []}`.
- `health.assess` → `health == "active"`, `last_cycle == 1`,
  `last_outcome == "42"` (coerced to str), `days_since_activity == 0`. No crash.

## Impact
Without this test, a regression that passed the raw int through (breaking the
`str | None` contract) or raised on the non-string would go undetected.

## Suggestion
Add `test_assess_trajectory_non_string_outcome` to `tests/test_robustness.py`.

## Tests
- Added: `test_assess_trajectory_non_string_outcome` in `tests/test_robustness.py`.
