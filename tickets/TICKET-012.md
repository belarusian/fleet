# TICKET-012: health.py — project_health-level tests for all 3 health states

## Title
The active/stalled/dead classification is only asserted at the `assess` level;
`project_health` (the API-parity wrapper) is never driven to each of the three
health states and its `health` field is never asserted.

## Evidence
- `fleet/health.py` — `project_health(ai_dir, repo_path)` delegates to `assess`
  and returns a `ProjectHealth` whose `health` field is set by
  `classify_health(days, has_traj)`.
- `tests/test_health.py` — `assess`-level state tests exist
  (`test_assess_active_project`, `test_assess_stalled`,
  `test_assess_dead_no_trajectories`, `test_assess_stalled_dead_boundary`),
  but the `project_health` tests (`test_project_health_name_derivation`,
  `test_project_health_repo_passthrough`, `test_project_health_now_default`)
  never assert `h.health`.

## Impact
The wrapper is the public entry point named in the briefing. If it ever
stopped delegating correctly (e.g. dropped the `now` default or mis-derived the
name), the existing wrapper tests would not catch a regression in the
classification, because they never check the `health` field.

## Suggestion
Add three tests that drive `project_health` to each state and assert
`h.health`:
- active: a project active 1 day ago -> `health == "active"`.
- stalled: a project idle 20 days -> `health == "stalled"`.
- dead: a project with only a gate log (no trajectories) -> `health == "dead"`.
