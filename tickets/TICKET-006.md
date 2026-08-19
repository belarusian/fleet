# TICKET-006: health.py — Add `project_health(ai_dir, repo_path=None)` wrapper for API parity

## Title
The cycle-1 briefing named the health entry point `project_health(ai_dir, repo_path)`, but the canonical implementation is `assess(name, ai_dir, repo, *, now)`. Callers that follow the briefing name have no entry point.

## Evidence
`fleet/health.py` exposes only `assess(name, ai_dir, repo=None, *, now=None)`. The public surface documented in `fleet/__init__.py` and the CLI (`fleet/cli.py::_assess_all`) call `assess(p.name, p.ai_dir)`. There is no `project_health` symbol, so the briefing-named API is missing.

## Impact
- The documented/briefing entry point does not exist; external callers (or the CLI, if it were to be simplified) cannot call `project_health(ai_dir)`.
- Name derivation is duplicated at every call site instead of being centralized.

## Suggestion
1. Add a thin `project_health(ai_dir, repo_path=None) -> ProjectHealth` wrapper that derives `name` from `ai_dir.parent.name` and delegates to `assess(name, ai, repo=repo_path)` (no `now` override, so it defaults to UTC now).
2. Keep `assess` as the canonical implementation (do not refactor it into the wrapper).
3. Add tests: `test_project_health_name_derivation`, `test_project_health_repo_passthrough`, `test_project_health_now_default`.
