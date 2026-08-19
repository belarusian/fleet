# TICKET-016: tests/test_cli.py — CLI `status` wiring (render_portfolio + --filter)

## Title
`fleet/cli.py` `status` is the user-facing entry point that composes
discover -> assess -> render_portfolio, but it has no test. We want a thin
wiring test that confirms `status` prints `render_portfolio(assessed)` and
honors `--filter` (active/stalled/dead/all).

## Evidence
- `fleet/cli.py` — `_cmd_status` calls `_assess_all(args.root)` (which runs
  `discover.discover` + `health.assess`), filters by `args.filter` when it is
  not "all", then `print(report.render_portfolio(healths))`.
- `tests/` — no `test_cli.py` exists; the CLI is only smoke-imported in
  `test_smoke.py`.

## Impact
A regression in the CLI wiring (e.g. forgetting to filter, printing the raw
list, or passing the wrong root) would not be caught, and the CLI is the next
build phase — a thin test now de-risks it.

## Suggestion
Add `tests/test_cli.py` that, for a known multi-project root (built with
`tests._fixtures.make_project`, days_ago 1/20/40 -> active/stalled/dead):
- patches `health.count_open_issues` (via `mock.patch.object`) so the
  open-issue column is deterministic, and pins the clock (patch
  `health.datetime` with a `datetime` subclass whose `now()` returns the fixed
  NOW, keeping `fromtimestamp` working) so the health/days columns are
  deterministic;
- asserts `cli.main(["status", "--root", root])` stdout (via `capsys`) equals
  `render_portfolio(assessed) + "\n"`;
- asserts `--filter <state>` yields only that state's rows for each of
  active/stalled/dead, and `--filter all` yields every row.
