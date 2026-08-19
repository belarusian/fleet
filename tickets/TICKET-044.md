# TICKET-044 — README health-threshold table

**Cycle:** 11 (Polish + Release, part 2)
**Type:** docs
**Status:** open

## Problem
`README.md` gives the health thresholds only as three prose bullets
(active / stalled / dead). A table is clearer and pins the exact day ranges.

## Target
Add a health-threshold table next to / replacing the three prose bullets, with
the EXACT semantics from `fleet/health.py` (`ACTIVE_MAX_DAYS = 7`,
`STALLED_MAX_DAYS = 30`):

| Health    | Condition |
|-----------|-----------|
| active    | has trajectories AND <= 7 days since activity |
| stalled   | has trajectories AND 8-30 days, OR has trajectories but no activity signal (days is None) |
| dead      | no trajectories, OR > 30 days since activity |

## Constraints
- Must match `classify_health` exactly: no trajectories -> dead; days is None
  -> stalled (if trajectories exist); days <= 7 -> active; days <= 30 ->
  stalled; else dead.
- Keep it consistent with the existing prose bullets (do not contradict them).

## Acceptance
- README has a health-threshold table with the exact day ranges + no-trajectories rule.
- Gate green (pytest + ruff + mypy).
