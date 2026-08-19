# TICKET-023 — CLI `snapshot` subcommand (save the current portfolio)

**Phase:** CLI + Snapshot, part 2
**Status:** DONE (Cycle 6)

## Problem
The `diff` workflow was incomplete end-to-end: `fleet diff` compares the
current portfolio against a saved snapshot, but there was no CLI way to *save*
a snapshot. Users had to call `snapshot.save_snapshot` by hand.

## Change
Add a `snapshot` subcommand to `fleet/cli.py` that wraps
`snapshot.save_snapshot`:

- `fleet snapshot [--root DIR] [--snapshot FILE]`
- `_cmd_snapshot(args)`: assess all projects under `--root` (via `_assess_all`),
  save them to `--snapshot` (default `snapshot.json`), print
  `saved N project(s) to <path>`, return 0.
- Wired into `main` dispatch.

## Tests (tests/test_cli.py)
- `test_cli_snapshot_saves_current_portfolio` — writes the assessed portfolio,
  round-trips via `load_snapshot`, asserts names/health/cycle/outcome match,
  and the stdout count + path.
- `test_cli_snapshot_creates_parent_dirs` — nested target path is created.
- `test_cli_snapshot_then_diff_is_end_to_end` — snapshot baseline + unchanged
  diff → `(no changes)` row.
- `test_cli_snapshot_then_diff_shows_changes` — snapshot baseline + added
  project → `added` row.
