# TICKET-041 — README has no end-to-end workflow example (status -> snapshot -> diff)

**Phase:** Cycle 10 synthesis audit (Polish + Release part 1)
**Status:** OPEN

## Problem
The README documents the three subcommands in isolation (and, per TICKET-040,
not even all of them) but never shows how they compose into the intended
workflow: take a baseline with `snapshot`, then `diff` against it to see what
changed. A newcomer cannot tell that `snapshot` produces the input `diff`
consumes.

## Evidence
- `README.md` CLI section (lines 16-20) lists `status` and `diff` as separate
  one-liners with no sequencing.
- `fleet/cli.py:1-25` module docstring describes the three subcommands and
  states `snapshot` is "the baseline that :func:`diff` compares against" — but
  this relationship is not surfaced in the README.
- `tests/test_cli.py:296` (`test_cli_snapshot_then_diff_is_end_to_end`) and
  `tests/test_cli.py:310` (`test_cli_snapshot_then_diff_shows_changes`) encode
  the intended workflow (snapshot then diff), confirming the relationship is
  real and load-bearing, yet it is absent from user docs.

## Impact
The README does not teach the primary use case (detecting drift between two
points in time). Users must infer from the `diff` comment that a snapshot must
exist first, and from nowhere in the README that `fleet snapshot` is how it is
created.

## Suggestion
Add a short "Workflow" subsection to `README.md` showing the canonical sequence,
e.g.:
    fleet status                 # current portfolio
    fleet snapshot --snapshot baseline.json   # save a baseline
    fleet diff --snapshot baseline.json       # see what changed since
Make the `--snapshot` path consistent across the example.

## Tests
- N/A (documentation change).
