# TICKET-046 — README reference to the example

**Cycle:** 11 (Polish + Release, part 2)
**Type:** docs
**Status:** open

## Problem
The README does not reference the new `examples/` tree, so a reader does not
know they can run `fleet status --root examples/` to see real output.

## Target
Add a short "Example" note in the README with the command
`fleet status --root examples/` (and optionally the `snapshot`/`diff` loop
against it). Note that health is mtime-based, so a freshly-checked-out tree
shows recent activity.

## Constraints
- Must reference the real `examples/` tree (TICKET-045).
- Do not add a `--json` flag or a `version` subcommand.

## Acceptance
- README has an "Example" note with `fleet status --root examples/`.
- Gate green (pytest + ruff + mypy).
