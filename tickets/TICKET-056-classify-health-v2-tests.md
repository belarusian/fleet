# TICKET-056: tests/test_health.py — unit tests for `classify_health_v2` (16 acceptance cases)

## Title
Add hermetic unit tests for `classify_health_v2` to `tests/test_health.py`,
covering all 16 acceptance cases from the Cycle 15 briefing. The classifier is
PURE, so tests construct `GitState(...)` directly — no git subprocess, no
`tmp_path`, no `fourseer` needed. Do NOT modify or remove any existing v1 test.

## Evidence
- `tests/test_health.py` has NO reference to `classify_health_v2`,
  `GitState`, or `DEAD_MIN_DAYS` (grep returns nothing). All existing tests
  target the v1 `classify_health` / `assess` / `project_health`.
- The input type is already importable and pure: `from fleet.gittest import
  GitState` (dataclass at `fleet/gittest.py:28`, `EMPTY_STATE = GitState((), 0)`
  at line 46).
- Existing test style (to match): module-level `from fleet import health`,
  plain `assert`-based functions, no classes needed for the pure classifier.

## Change
Add a `from fleet.gittest import GitState` import and a set of test functions
(e.g. `test_classify_health_v2_*`) pinning, at minimum, these 16 cases:

  1. unmerged `build*` branch (any recency) -> "stranded"
  2. unpushed commits > 0 (any recency) -> "stranded"
  3. recent (<=7d) + "max_steps_reached", no git -> "active"
  4. recent + unmerged branch + "max_steps_reached" -> "stranded" (stranded beats active)
  5. recent + "exit:task_complete", nothing in flight -> "paused"
  6. recent + last_outcome is None, nothing in flight -> "paused"
  7. 30+ days, nothing in flight -> "dead"
  8. 8-30 days idle, nothing in flight -> "paused" (benign; not yet dead)
  9. days is None, nothing in flight -> "dead" (no activity signal, abandoned)
 10. days is None + "max_steps_reached" -> "active" (work in flight)
 11. 8-30 days + "max_steps_reached", no git -> "active" (in flight, not recent)
 12. unpushed commits + 30+ days -> "stranded" (stranded beats dead)
 13. boundary: 7d + "max_steps_reached" -> "active"; 7d + "exit:task_complete" -> "paused"
 14. boundary: 30d, nothing in flight -> "dead"; 29d, nothing in flight -> "paused"
 15. canary (alloc-pipeline shape): unmerged `build42/...` + unpushed -> "stranded"
 16. canary (deepseek-deharness shape): recent + "exit:task_complete", nothing in flight -> "paused"

Use `EMPTY_STATE` (or `GitState((), 0)`) for the "no git" cases; construct
`GitState(("build42/x",), 0)` / `GitState((), 3)` for the git-signal cases.

## Impact
Without these tests the v2 classifier's most-severe-wins ordering and its
boundaries (7d / 30d / None) are unpinned. A regression that, e.g., lets
`active` beat `stranded`, or misclassifies the 8-29-day band as `dead`, would
ship silently and corrupt the Cycle 16 report and Cycle 17 canaries.

## Suggestion
Write one focused test per acceptance case (or group the two boundary pairs
13/14). Assert the exact returned string. Keep the classifier pure in tests:
no `mock.patch`, no filesystem. Gate: `pytest tests/ -x -q`,
`ruff check fleet/`, `mypy fleet/ --ignore-missing-imports`.
