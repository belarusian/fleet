# TICKET-067: CLI v2 filter — `paused` untested, and the v1/v2 Health-column divergence is unpinned

## Title
The only v2 consumer (the CLI `--filter` path) is tested for `stranded` only; `paused` is
untested, and the divergence between the v2 filter and the v1 Health column is not pinned.

## Evidence
- `fleet/cli.py:131-140` — `--filter stranded|paused` selects rows by
  `classify_health_v2(days, last_outcome, git_state) == args.filter`. This is the ONLY place in
  the codebase that calls `classify_health_v2`.
- `tests/test_cli.py:149` (`test_cli_status_filter_stranded`) covers `--filter stranded` but
  does so by **mocking** `cli.read_gitstate` (line 170). There is **no** `test_cli_status_filter_paused`
  — the `paused` branch of the same `if` (cli.py:131) is untested.
- The filtered row is rendered by `render_portfolio` (cli.py:141), which prints `h.health`
  (fleet/report.py:117) — the **v1** class. So a project selected by `--filter stranded` (v2)
  can still display a v1 class (e.g. `active` or `stalled`) in the Health column. This v1/v2
  divergence in the same row is never asserted by any test.

## Impact
- The `paused` filter branch is untested: a regression there (wrong class, wrong git_state
  lookup) would ship undetected.
- The fact that a v2-filtered row displays a v1 Health cell is a real, user-visible inconsistency
  (the row was selected as "stranded" but reads "active"). No test pins this, so a future change
  that "fixes" it (or breaks it) would go unnoticed.

## Suggestion
1. Add `test_cli_status_filter_paused` mirroring `test_cli_status_filter_stranded`, with a
   project whose v2 class is `paused` (recent + `exit:task_complete`, clean git state) and
   assert only that row is printed.
2. Add an assertion (in either filter test) pinning the Health-column value of a v2-filtered
   row, so the v1/v2 divergence is explicit and intentional rather than accidental.
