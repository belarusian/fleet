# TICKET-015: tests/test_integration.py — end-to-end discover -> assess -> render_portfolio

## Title
There is no test that runs the full Classification + Report pipeline together:
`discover.discover(root)` -> `health.assess(name, ai_dir, now=NOW)` over every
discovered project -> `report.render_portfolio(assessed)`. The Classification
half (health) and the Report half (report) are only tested in isolation.

## Evidence
- `fleet/discover.py` — `discover(root) -> list[Project]` (sorted by name).
- `fleet/health.py` — `assess(name, ai_dir, repo=None, *, now=None) -> ProjectHealth`;
  `now=` is the deterministic reference clock.
- `fleet/report.py` — `render_portfolio(healths) -> str`, sorted by
  last-activity descending (no-activity last).
- `tests/` — `test_discover.py`, `test_health.py`, `test_report.py` each test one
  module in isolation; nothing composes all three.

## Impact
A regression at the seam (e.g. `assess` returning a `ProjectHealth` whose
`last_activity` is `None` when it should be set, or `discover` returning a name
that `assess` mis-derives) would pass every isolated test but break the real
portfolio the user sees.

## Suggestion
Add `tests/test_integration.py` that:
- builds a multi-project root with `tests._fixtures.make_project`, varying
  `days_ago` (e.g. 1, 20, 40) so the projects land in distinct health states
  (active/stalled/dead) AND have distinct last-activity timestamps;
- runs `discover.discover(root)` then `health.assess(p.name, p.ai_dir, now=NOW)`
  for each (patching `health.count_open_issues` for a deterministic open-issue
  column);
- feeds the resulting `ProjectHealth` list into `report.render_portfolio`;
- asserts the full table is correctly sorted (last-activity desc) and
  correctly formatted (exact expected markdown).

Note: every *discovered* project has at least one activity file (trajectories
or a gate log), so `last_activity` is never `None` through the real pipeline;
the no-activity-last ordering is already pinned at the report unit level
(`test_report.py::test_render_portfolio_no_activity_last`).
