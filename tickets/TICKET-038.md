# TICKET-038 — Robustness: `cycles.out` with a malformed header

**Phase:** Cycle 9 synthesis audit
**Status:** RESOLVED (test added)

## Problem
A `cycles.out` header whose timestamp is not `HH:MM:SSZ` (e.g.
`========== CYCLE 3  not-a-time ==========`) was not pinned. fourseer's
`_HEADER_RE` (see `fourseer-parsers/parse/cycles_out.py`) does not match such a
line, so the cycle is not recorded and any following `OUTER` lines are ignored
(`current is None`). fleet must report `last_cycle is None` /
`last_outcome is None` gracefully.

## Evidence
- Probed a project with only a `cycles.out` containing a malformed header plus
  an `OUTER outcome:` line.
- `health.assess` → `health == "dead"` (no trajectories), `last_cycle is None`,
  `last_outcome is None`, `days_since_activity == 0` (the file exists on disk,
  so it contributes an mtime signal). No crash.

## Impact
Without this test, a regression that crashed on a malformed header, or that
partially parsed the `OUTER` line into a bogus cycle, would go undetected.

## Suggestion
Add `test_assess_malformed_cycles_out_header` to `tests/test_robustness.py`.

## Tests
- Added: `test_assess_malformed_cycles_out_header` in `tests/test_robustness.py`.
