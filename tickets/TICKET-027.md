# TICKET-027 — Confirm CLI exit codes

**Phase:** CLI + Snapshot, part 2
**Status:** DONE (Cycle 6)

## Problem
The briefing asked to confirm `main` returns correct exit codes:
`status`/`diff` → 0 on success, `diff` → 2 on missing snapshot.

## Confirmation
- `status` → 0 on success (already tested in Cycle 4).
- `diff` → 0 on success, 2 on missing snapshot (already tested in Cycle 5:
  `test_cli_diff_missing_snapshot`).
- `snapshot` → 0 on success (new, tested in Cycle 6:
  `test_cli_snapshot_saves_current_portfolio` and the end-to-end tests).

## Change
- No code change needed for exit codes; the new `snapshot` subcommand returns 0
  on success, consistent with the others.

## Tests
- New `snapshot` tests assert `rc == 0` on success.
- Existing `status`/`diff` tests already pin the 0/2 semantics.
