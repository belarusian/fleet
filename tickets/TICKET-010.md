# TICKET-010: tests/test_health.py — Tests for the `project_health` wrapper

## Title
The new `project_health` wrapper (TICKET-006) needs dedicated tests for name derivation, repo passthrough, and the `now` default.

## Evidence
`fleet/health.py::project_health` derives `name` from `ai_dir.parent.name`, forwards `repo_path` to `assess(repo=...)`, and omits `now` so `assess` defaults to UTC now. No tests exercise this path.

## Impact
- A regression in name derivation (e.g. using `ai_dir.name` instead of `ai_dir.parent.name`) or in the repo passthrough would go undetected.

## Suggestion
Add tests:
- `test_project_health_name_derivation` — `h.name == <parent dir name>`.
- `test_project_health_repo_passthrough` — `count_open_issues` is called with the given repo.
- `test_project_health_now_default` — `assess` is invoked without a `now` keyword (so it defaults to UTC now).
