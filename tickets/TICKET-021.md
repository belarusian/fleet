# TICKET-021: tests/test_cli.py — CLI `diff` subcommand wiring (_cmd_diff + main dispatch)

## Title
`fleet/cli.py` `diff` is the user-facing entry point that composes
load_snapshot -> assess -> snapshot_diff -> render_diff, but it has no test.
`tests/test_cli.py` only covers the `status` subcommand.

## Evidence
- `fleet/cli.py:76` — `_cmd_diff`:
    - expands `args.snapshot` to a `Path`;
    - if the file is missing, prints `error: snapshot not found: {path}` to
      stderr and returns `2`;
    - otherwise `load_snapshot`, `_assess_all(args.root)`,
      `snapshot_mod.snapshot_diff(snap, current)`,
      `print(snapshot_mod.render_diff(rows))`, returns `0`.
- `fleet/cli.py:89` — `main` dispatches `args.command == "diff"` to `_cmd_diff`.
- `tests/test_cli.py` — five tests, all `status`. No `diff` invocation, no
  missing-snapshot path, no `--snapshot` arg handling.

## Impact
A regression in the diff wiring (e.g. wrong exit code on a missing snapshot,
printing to stdout instead of stderr for the error, passing the snapshot and
current arguments to `snapshot_diff` in the wrong order, or forgetting to
`expanduser` the snapshot path) would not be caught. The `diff` subcommand is
the second user-facing command and is currently the only untested CLI path.

## Suggestion
Add tests to `tests/test_cli.py` that:
- build a multi-project root with `tests._fixtures.make_project`, write a
  snapshot with `snapshot.save_snapshot`, then run
  `cli.main(["diff", "--root", root, "--snapshot", str(snap_path)])` and assert
  rc == 0 and stdout equals `render_diff(snapshot_diff(snap, assessed)) + "\n"`
  (pin the clock and patch `health.count_open_issues` as the status tests do);
- run `cli.main(["diff", "--root", root, "--snapshot", str(missing)])` and
  assert rc == 2 and the stderr message contains `snapshot not found`;
- assert `--snapshot` defaults to `snapshot.json` (e.g. by pointing CWD at a
  temp dir or by checking the parser default in `_build_parser`).
