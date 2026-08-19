# TICKET-034 — Robustness: project whose ai/ is a file (not a dir)

**Phase:** Cycle 8 synthesis audit
**Status:** RESOLVED (tests added)

## Problem
A project directory whose `ai/` entry is a *file* rather than a directory was
not covered. `discover` must skip it (it is not a project), and `assess` on
such a path must not crash — it should report `dead` with all-`None` metrics.

## Evidence
- `fleet/discover.py:is_project`: `if not ai.is_dir(): return False` — a file
  is never a project.
- `fourseer/load.py:load_run`: `load_trajectories(ai/"trajectories")` on a
  non-dir yields `[]`; `_find_gate_log`/`_find_cycles_out` return `None`
  (no `is_file()` match) → empty `Run`.
- Probed: `discover` on a root containing `<p>/ai` (a file) → `[]`;
  `is_project(<p>/ai)` → `False`; `assess("p", <p>/ai)` →
  `health="dead"`, all cycle/activity metrics `None`.

## Impact
Without tests, a regression that made `is_project` or `assess` raise on a
non-directory `ai/` path (e.g. an unguarded `iterdir`) would go undetected.

## Suggestion
Add `test_discover_ignores_ai_as_file` and `test_assess_ai_as_file` to
`tests/test_robustness.py`.

## Tests
- Added: `test_discover_ignores_ai_as_file`, `test_assess_ai_as_file` in
  `tests/test_robustness.py`.
