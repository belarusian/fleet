# TICKET-033 — Robustness: wall-clock-killed cycle (header, no OUTER) → outcome None

**Phase:** Cycle 8 synthesis audit
**Status:** RESOLVED (tests added)

## Problem
A `cycles.out` cycle killed by the wall-clock alarm writes a header line but
NO `OUTER` lines. `fourseer.parse_cycles_out` returns such a cycle with
`outcome=None` and `trajectory_path=None`. fleet must report this gracefully:
the killed cycle's number is still the last cycle, but its outcome is `None`
(so the outcome falls back to the most-recent trajectory's outcome, or stays
`None` when there is no trajectory).

## Evidence
- `fourseer/parse/cycles_out.py:parse_cycles_out`: a header line always
  appends a `CycleRecord(outcome=None, trajectory_path=None)`; only `OUTER`
  lines populate them.
- Probed: a project with a trajectory (outcome `exit:task_complete`) plus a
  killed `CYCLE 5` → `last_cycle=5`, `last_outcome="exit:task_complete"`
  (fallback), `health="active"`.
- Probed: a project with ONLY a killed `CYCLE 5` (no traj/gate) →
  `last_cycle=5`, `last_outcome=None`, `health="dead"`, and `discover` does
  not find it (is_project needs trajectories or a gate log).

## Impact
Without tests, a change to the cycles-out parser (e.g. dropping header-only
cycles) or to the outcome-fallback priority in `_last_cycle_and_outcome`
would go undetected.

## Suggestion
Add `test_assess_wall_clock_killed_cycle` (with a trajectory) and
`test_assess_wall_clock_killed_cycle_only` (no trajectory) to
`tests/test_robustness.py`.

## Tests
- Added: `test_assess_wall_clock_killed_cycle`,
  `test_assess_wall_clock_killed_cycle_only` in `tests/test_robustness.py`.
