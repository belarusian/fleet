# TICKET-014: report.py — tests/test_report.py for render_portfolio

## Title
`fleet.report.render_portfolio` had no dedicated test module. Add
`tests/test_report.py` covering the four behaviors the briefing calls out.

## Evidence
- `fleet/report.py` — `render_portfolio(healths)` sorts via `_sort_key`
  (last-activity desc, no-activity last), renders a header-only
  "(no projects discovered)" row for empty input, and formats `None`
  `last_cycle` / `last_outcome` / `days_since_activity` as `-`.
- Before this cycle there was no `tests/test_report.py`.

## Scope (implemented + verified this cycle)
- `test_render_portfolio_empty_input` — header + separator + single
  "(no projects discovered)" row, exactly 3 lines.
- `test_render_portfolio_mixed_health_ordering` — rows ordered by the
  health tie-break when timestamps are equal.
- `test_render_portfolio_no_activity_last` — a `last_activity is None` row
  sorts after every row that has activity.
- `test_render_portfolio_full_table_none_fields` — a multi-project table
  where `None` fields render as `-` and row order is preserved.

## Status
Implemented by the auditor spoke (commit `a5d403a`); verified against the
briefing. See TICKET-013 for the additional primary-sort test added on top.
