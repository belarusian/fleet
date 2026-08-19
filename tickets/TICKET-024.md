# TICKET-024 — Confirm `--root` defaults to `~/AI` on every subcommand

**Phase:** CLI + Snapshot, part 2
**Status:** DONE (Cycle 6)

## Problem
The briefing asked to confirm that `--root` defaults to `~/AI`. This was
already true in the parser (status/diff) but untested, and the new `snapshot`
subcommand must honor it too.

## Change
- `snapshot` subcommand's `--root` uses `default="~/AI"` (consistent with
  status/diff).
- Documented in the module docstring: "`--root` defaults to `~/AI` on every
  subcommand."

## Tests (tests/test_cli.py)
- `test_cli_root_defaults_to_home_ai` — parses each of `status`, `snapshot`,
  `diff` with no `--root` and asserts `args.root == "~/AI"`.
- `test_cli_snapshot_default_is_snapshot_json` — the snapshot subcommand's
  `--snapshot` default is `snapshot.json`.
