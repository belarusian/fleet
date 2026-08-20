# TICKET-062: tests/test_report.py — Git column tests (extend, do not modify)

## Title
Extend `tests/test_report.py` to pin the new opt-in `Git` column of
`render_portfolio`. Do NOT modify any existing test (they pin the 6-column
byte-identical output).

## Evidence
- `tests/test_report.py` has 5 existing tests pinning the 6-column table
  (empty input, mixed ordering, no-activity-last, full table with `-`,
  last-activity-desc). These must stay green.
- The new `render_portfolio(healths, git_states)` behavior is untested.

## Change
Add tests to `tests/test_report.py` (import `GitState`, `EMPTY_STATE` from
`fleet.gittest`):
- `render_portfolio(healths)` with no `git_states` is byte-identical to the
  6-column form (assert the exact 6-column header + a row).
- With a `git_states` dict: header has 7 columns ending in ` Git |`; separator
  ends in `---|`; a clean project (`EMPTY_STATE`) renders `-` in the Git cell.
- `unmerged:build42/x`, `unpushed:3`, and the combined
  `unmerged:build42/x+build43/y,unpushed:3` render exactly.
- A project name absent from the `git_states` dict renders `-` (EMPTY_STATE
  default).
- Empty input WITH `git_states` yields the 7-column no-projects row.
