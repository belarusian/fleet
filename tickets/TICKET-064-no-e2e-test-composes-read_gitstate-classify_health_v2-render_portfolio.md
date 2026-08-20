# TICKET-064: No end-to-end test composes read_gitstate -> classify_health_v2 -> render_portfolio

## Title
The Cycle-17 target pipeline is never exercised as a single composed path.

## Evidence
The stated target is:
`discover -> assess -> classify_health_v2(read_gitstate(...)) -> render_portfolio(healths, git_states)`.

No test runs this as one composed path:
- `tests/test_integration.py` stops at `discover -> assess -> render_portfolio` and uses **v1**
  (`assess` calls `classify_health`, fleet/health.py:324). It never imports `gittest` or
  `classify_health_v2`.
- `tests/test_cli.py:149` (`test_cli_status_filter_stranded`) is the only test that touches
  `classify_health_v2`, and it does so by **mocking** `cli.read_gitstate`
  (`mock.patch.object(cli, "read_gitstate", side_effect=_fake_read_gitstate)`) and only
  exercising the `--filter` branch (fleet/cli.py:131-140). It never feeds a real
  `read_gitstate` result through `classify_health_v2` into `render_portfolio`.
- `tests/test_gittest.py` tests `read_gitstate` in isolation (real git repos) but never feeds
  the result into `classify_health_v2` or `render_portfolio`.
- `tests/test_health.py` (TICKET-056 block) tests `classify_health_v2` in isolation with
  hand-built `GitState(...)` values, never a real `read_gitstate` output.

So the three links (`read_gitstate`, `classify_health_v2`, `render_portfolio`) are each tested
alone, but the seams between them are untested.

## Impact
A regression in how a real git state maps to a v2 class and then into the rendered table would
ship undetected. The "integration" this cycle claims to verify does not exist as a composed
test, so the cycle cannot actually confirm the pipeline works end to end.

## Suggestion
Add a test (e.g. in `tests/test_integration.py`) that:
1. builds a real git repo under `tmp_path` with an unmerged `build*` branch (reuse the helpers
   in `tests/test_gittest.py`),
2. calls `gittest.read_gitstate(repo)` for real,
3. feeds that `GitState` into `health.classify_health_v2(days, outcome, git_state)`,
4. passes the resulting class + `git_states` mapping into `report.render_portfolio`,
5. asserts the v2 class and the `unmerged:<branch>` Git cell both appear in the rendered table.
