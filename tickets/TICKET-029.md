# TICKET-029 — Robustness: fleet must not crash on degenerate project layouts

**Phase:** Cycle 7 synthesis audit
**Status:** OPEN

## Problem
The fleet scanner should gracefully handle several degenerate project layouts
that can occur in practice. This ticket tracks the edge cases that need
explicit test coverage to confirm `fleet` does not crash:

1. **No trajectories (gate-log-only project)** — already covered by
   `test_assess_dead_no_trajectories` (test_health.py). ✓
2. **Missing gate log (trajectories-only project)** — a project with
   `trajectories/*.json` but no `*gate*.md` file. `fourseer.load_run` returns
   an empty `GateLog()`. `assess` should work. **NOT tested.**
3. **Empty root** — `discover.discover` on an empty directory returns `[]`.
   Already covered by `test_discover_empty_root`. ✓
4. **Corrupt trajectory JSON** — a `trajectories/` dir containing a `.json`
   file with invalid JSON. `fourseer.load_trajectories` skips corrupt files
   (trajectories.py: `except (OSError, json.JSONDecodeError): continue`).
   `assess` should not crash. **NOT tested.**
5. **Project with only a cycles.out** — a project with `cycles.out` but no
   trajectories and no gate log. `discover.is_project` requires trajectories
   OR a gate log, so this project would NOT be discovered. However, if
   `assess` is called directly on such a dir, it should not crash.
   **NOT tested.**

## Evidence
- `fourseer/parse/trajectories.py`: corrupt JSON is skipped silently.
- `fourseer/load.py`: missing gate log → `GateLog()` (empty).
- `fleet/discover.py:is_project`: requires `_has_trajectories(ai) or _has_gate_log(ai)`.
- `fleet/health.py:assess`: calls `fourseer.load_run(ai)` which handles all
  missing-file cases gracefully.

## Impact
Without explicit tests, a regression in any of these paths (e.g., a change to
`load_trajectories` that raises instead of skipping) would go undetected until
production.

## Suggestion
Add a test module `tests/test_robustness.py` with one test per edge case:
- `test_assess_trajectories_only_no_gate_log`
- `test_assess_corrupt_trajectory_json`
- `test_assess_only_cycles_out`
- `test_assess_empty_ai_dir` (no trajectories, no gate log, no cycles.out)

## Tests
- New: `tests/test_robustness.py`
