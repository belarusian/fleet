# TICKET-020: tests/test_snapshot.py — render_diff markdown table + no-changes case

## Title
`fleet/snapshot.py` `render_diff(rows)` renders the diff rows as a markdown
table and has a special "no changes" branch. It has no test.

## Evidence
- `fleet/snapshot.py:167` — `render_diff`:
    - always emits the header `| Project | Status | Detail |` + separator;
    - filters out `status == "unchanged"` rows (`shown`);
    - when `shown` is empty, emits the single row `| (no changes) | - | - |`;
    - otherwise emits one row per shown row, using `r.detail or '-'` for the
      Detail column.
- `tests/` — no test calls `render_diff` or asserts on its markdown output.

## Impact
A regression (e.g. leaking `unchanged` rows into the table, breaking the
`(no changes)` sentinel, or a malformed markdown row) would produce a broken
diff table with no test to catch it. The `detail or '-'` fallback for empty
detail (the `unchanged`/no-detail case) is untested.

## Suggestion
Add tests that call `render_diff` with:
- a mixed list of `added` / `removed` / `changed` / `unchanged` `DiffRow`s ->
  assert the exact markdown: header present, `unchanged` rows absent, and the
  `added`/`removed`/`changed` rows present with correct Status and Detail;
- a list containing only `unchanged` rows (or an empty list) -> assert the
  output is exactly the header + `| (no changes) | - | - |`;
- a `changed` row with an empty `detail` -> assert the Detail column renders as
  `-`.
