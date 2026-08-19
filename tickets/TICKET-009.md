# TICKET-009: tests/test_discover.py — Edge-case hardening (empty root, non-project dirs, gate-log variants, single trajectory)

## Title
`discover` lacks tests for the edge cases named in the cycle-2 briefing: empty root, a root holding only non-project dirs, an `ai/` with a gate log but no `## Cycle` block, multiple gate logs (fourseer prefers `cycle-001`), and a trajectory dir with a single file.

## Evidence
`tests/test_discover.py` covers the happy path, sorting, non-project filtering, gate-log-only, missing root, nested group, and the `is_project` predicate — but not the five edge cases above.

## Impact
- Regression risk: a change to the depth walk, the `is_project` predicate, or the fourseer gate-log preference could silently break one of these cases with no test to catch it.

## Suggestion
Add tests:
- `test_discover_empty_root` — empty root dir yields `[]`.
- `test_discover_root_with_only_non_project_dirs` — dirs without a qualifying `ai/` yield `[]`.
- `test_discover_gate_log_without_cycle_block` — a gate log with no `## Cycle` header is still a project.
- `test_discover_multiple_gate_logs_prefers_cycle_001` — with two gate logs, `fourseer.load_run` prefers the `cycle-001` file.
- `test_discover_trajectory_dir_with_single_file` — one trajectory JSON is a valid project.
