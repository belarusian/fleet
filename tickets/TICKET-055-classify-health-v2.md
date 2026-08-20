# TICKET-055: fleet/health.py — add pure `classify_health_v2` (four classes, most-severe-wins)

## Title
Add `classify_health_v2(days: int | None, last_outcome: str | None, git_state: GitState) -> str`
to `fleet/health.py`: a PURE function (no I/O) returning exactly one of
`"stranded"` / `"active"` / `"paused"` / `"dead"`. This is the Cycle 15 target
(Health v2: Outcome + Classify). It is NOT wired into `assess` this cycle.

## Evidence
- `fleet/health.py` has NO `classify_health_v2` (grep for the name returns
  nothing). Only the v1 `classify_health(days, has_trajectories)` exists
  (line 183).
- `fleet/health.py` has NO `DEAD_MIN_DAYS` constant. Existing constants are
  `ACTIVE_MAX_DAYS = 7` (line 23) and `STALLED_MAX_DAYS = 30` (line 24).
- `fleet/health.py` does NOT import `GitState` (no `from fleet.gittest import ...`).
  The input type already exists: `fleet/gittest.py` defines
  `@dataclass(frozen=True) GitState` (line 28) with fields
  `unmerged_build_branches: tuple[str, ...]` (line 41) and
  `unpushed_commits: int` (line 42), plus `EMPTY_STATE = GitState((), 0)`
  (line 46).
- The `last_outcome` half of the Build Order is already satisfied:
  `ProjectHealth.last_outcome` exists and is populated from fourseer via
  `_last_cycle_and_outcome`. Only the classifier is missing.
- Outcome semantics (from the seed `fourseer.taxonomy`): the ONLY outcome that
  counts as "work in flight" is the exact string `"max_steps_reached"`.
  `"exit:task_complete"`, `execution_error*`, and `repeated_format_error*`
  are NOT in flight.

## Change
In `fleet/health.py`:
- Add module constant `DEAD_MIN_DAYS = 30` next to the existing thresholds
  (reuse `ACTIVE_MAX_DAYS = 7`; do NOT redefine it).
- Add `from fleet.gittest import GitState` (type-only import is fine).
- Add the pure function: