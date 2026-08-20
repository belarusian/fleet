# TICKET-063: tests/test_cli.py — `--filter stranded` + Git column tests

## Title
Extend `tests/test_cli.py` to pin the `status --filter stranded` selection and
the always-present Git column. Update the existing status expected-computations
to pass `_git_states(root)` (the tmp projects are not git repos, so every Git
cell is `-`). Do NOT break existing tests.

## Evidence
- `tests/test_cli.py` `test_cli_status_matches_render_portfolio` and
  `test_cli_status_filter_active/stalled/dead/all` currently compute the
  expected table as `report.render_portfolio(<rows>)` (6-column). Once
  `_cmd_status` always passes `git_states`, the CLI output is 7-column, so
  these expected computations must become
  `report.render_portfolio(<rows>, _git_states(root))`.
- `test_cli_open_issues_always_zero` stays UNCHANGED (Git is appended at the
  end, so `open_issues` is still column index 4).
- The new `--filter stranded` and the Git column are untested.

## Change
In `tests/test_cli.py`:
- Add helper `_git_states(root)` =
  `{p.name: read_gitstate(p.path) for p in discover.discover(root)}`.
- Change the expected computations in `test_cli_status_matches_render_portfolio`
  and `test_cli_status_filter_active/stalled/dead/all` to
  `report.render_portfolio(<rows>, _git_states(root))`.
- Add `test_cli_status_filter_stranded`: build the 3-project root, patch
  `cli.read_gitstate` with a side_effect mapping `Path(path).name` ->
  `GitState(("build42/x",), 0)` for "alpha" and `EMPTY_STATE` for the others,
  run `status --filter stranded`, and assert only alpha's row is printed
  (equals `report.render_portfolio([alpha], git_states) + "\n"`).
- Add `test_cli_status_shows_git_column`: run `status` (default filter) with a
  patched `read_gitstate` giving one project an unmerged branch; assert the
  header contains ` Git |` and the row contains `unmerged:build42/x`.
