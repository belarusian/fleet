# TICKET-042 — No test pins the CLI surface (three subcommands registered + each --help works)

**Phase:** Cycle 10 synthesis audit (Polish + Release part 1)
**Status:** OPEN

## Problem
There is no test that pins the CLI surface itself: that exactly the three
subcommands `status`, `snapshot`, and `diff` are registered, and that each
subcommand's `--help` renders without error. Existing tests exercise the
*behavior* of each subcommand but never assert the *shape* of the parser.

## Evidence
- `fleet/cli.py:48,62,74` register exactly three subcommands: `status`,
  `snapshot`, `diff`.
- `tests/test_cli.py` has no test that (a) enumerates the registered
  subcommands, or (b) invokes `<cmd> --help` for each. `grep -rn --help tests/`
  returns nothing.
- `tests/test_cli.py:332-334` (`test_cli_root_defaults_to_home_ai`) iterates
  `("status", "snapshot", "diff")` only to check the `--root` default — it does
  not assert these are the *only* registered subcommands, nor that `--help`
  works.
- Manually verified: `cli._build_parser().parse_args([cmd, "--help"])` exits 0
  for each of the three subcommands (argparse `--help` prints and exits 0).

## Impact
A regression that drops a subcommand from `_build_parser` (e.g. `snapshot`
accidentally removed), renames one, or breaks a subparser's argument setup so
that `--help` raises, would not be caught by the current suite. The CLI surface
is the public contract for the `fourseer`/`fleet` console script and is
undocumented-by-test.

## Suggestion
Add a test (e.g. `test_cli_subcommand_surface` in `tests/test_cli.py`) that:
1. Asserts the set of registered subcommands is exactly
   `{"status", "snapshot", "diff"}` (read from the parser's subparsers action).
2. For each subcommand, asserts `cli.main([cmd, "--help"])` exits 0 (capture
   stdout; argparse `--help` raises `SystemExit(0)`).

## Tests
- Add: `test_cli_subcommand_surface` in `tests/test_cli.py`.
