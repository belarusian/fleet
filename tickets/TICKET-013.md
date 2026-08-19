# TICKET-013: report.py — test the primary last-activity-descending sort

## Title
`tests/test_report.py::test_render_portfolio_mixed_health_ordering` gives every
row the SAME `last_activity` timestamp, so it only exercises the health
tie-break — not the primary "sort by last-activity descending" behavior that
the briefing calls out.

## Evidence
- `fleet/report.py` — `_sort_key` returns `(time_key, -ts, health_order, name)`:
  the FIRST key is the last-activity timestamp (descending), the health order
  is only the THIRD key (a tie-break).
- `tests/test_report.py` — `test_render_portfolio_mixed_health_ordering` builds
  all three rows with `last_activity=NOW`, so `-ts` is identical for every row
  and the observed ordering comes entirely from the health tie-break.

## Impact
A regression that broke the primary time sort (e.g. sorting ascending, or
ignoring `last_activity`) would still pass the current test, because the test
never varies the timestamps.

## Suggestion
Add a test that gives the rows DISTINCT `last_activity` timestamps and asserts
they render most-recent-first, independent of health. E.g. a `dead` project
active 1 day ago must sort ABOVE an `active` project idle 20 days, proving the
time key dominates the health key.
