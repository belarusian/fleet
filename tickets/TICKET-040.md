# TICKET-040 — README CLI section omits the `snapshot` subcommand

**Phase:** Cycle 10 synthesis audit (Polish + Release part 1)
**Status:** OPEN

## Problem
The README's CLI section documents only two subcommands, but the CLI registers
three. `snapshot` is a first-class subcommand (it is the baseline that `diff`
compares against) yet it is absent from the user-facing CLI reference.

## Evidence
- `fleet/cli.py:48` registers `status`, `fleet/cli.py:62` registers `snapshot`,
  `fleet/cli.py:74` registers `diff` — three subcommands via
  `sub.add_parser(...)`.
- `README.md:18-19` documents only:
  - `fleet status [--root ~/AI] [--filter active|stalled|dead|all]`
  - `fleet diff   # compare against a saved snapshot JSON`
  There is no `fleet snapshot` line, so a reader cannot discover the subcommand
  from the README.

## Impact
A user who wants to save a baseline (the input `diff` consumes) has no way to
learn that `fleet snapshot` exists from the documentation. The `diff` line even
references "a saved snapshot JSON" without ever saying how to create one.

## Suggestion
Add the `snapshot` line to the `## CLI` block, matching the real CLI (verified
via `fleet snapshot --help`):
    fleet snapshot [--root ~/AI] [--snapshot SNAPSHOT]
Keep the existing `status` and `diff` lines. Do not invent flags that do not
exist.

## Tests
- N/A (documentation change). The CLI-surface guard (TICKET-042) pins that
  `snapshot` is registered and its `--help` works.
