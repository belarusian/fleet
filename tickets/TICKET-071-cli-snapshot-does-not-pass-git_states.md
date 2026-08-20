# TICKET-071: fleet snapshot CLI does not pass git_states, so saved snapshots carry no health_v2

## Title
`_cmd_snapshot` calls `save_snapshot(healths, args.snapshot)` without `git_states`, so the CLI
never computes v2 classes for the snapshot it writes.

## Evidence
- `fleet/cli.py:148-152` — `_cmd_snapshot` does:
    `healths = _assess_all(args.root)`
    `path = snapshot_mod.save_snapshot(healths, args.snapshot)`
  It does not call `_git_states` and does not pass a `git_states` argument.
- `fleet/cli.py:116-120` — `_git_states(root)` already exists and returns
  `{p.name: read_gitstate(p.path) for p in discover.discover(root)}`; it is used by
  `_cmd_status` (`fleet/cli.py:129`) but not by `_cmd_snapshot`.
- `fleet/snapshot.py:65` — `save_snapshot` currently has no `git_states` parameter (see
  TICKET-069), so the CLI has nothing to pass yet.

## Impact
Running `fleet snapshot` produces a v1-only snapshot. The v2 snapshot shape is unreachable from
the CLI even after the library changes in TICKET-068/069, because the only production caller of
`save_snapshot` does not supply the git state needed to derive `health_v2`.

## Suggestion
In `_cmd_snapshot`, read the git state and pass it through:
    `healths = _assess_all(args.root)`
    `git_states = _git_states(args.root)`
    `path = snapshot_mod.save_snapshot(healths, args.snapshot, git_states=git_states)`
This mirrors the existing `_cmd_status` pattern (`fleet/cli.py:128-129`). Add a CLI test that
asserts the written snapshot JSON contains a `health_v2` key per project.
