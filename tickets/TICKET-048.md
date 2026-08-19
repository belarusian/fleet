# TICKET-048: Add a top-level `--version` flag to the fleet CLI

## Title
`fleet --version` should print the package version and exit 0.

## Evidence
- Before this change, `fleet --version` failed: the top-level parser had no
  `--version` argument and `command` was `required=True`, so argparse raised
  `error: the following arguments are required: command` (exit 2).
- `fleet/__init__.py` defines `__version__ = "0.1.0"` and `pyproject.toml`
  has `version = "0.1.0"` (in sync; first release, no bump warranted).

## Change
- `fleet/cli.py`: in `_build_parser`, add
  `parser.add_argument("--version", action="version", version=f"fleet {__version__}",
  help="print the fleet version and exit")` to the **top-level** parser (import
  `__version__` from `fleet`).
- This is a **flag, not a subcommand**: `action="version"` prints to stdout and
  raises `SystemExit(0)`. It does not register a subcommand, so the guard test
  `tests/test_cli.py::test_cli_registered_subcommands_are_exactly_three`
  (asserts `set(sub.choices) == {"status", "snapshot", "diff"}`) stays green.

## Acceptance
- `fleet --version` exits 0 and prints exactly `fleet 0.1.0`.
- The exactly-three-subcommands guard test still passes.
