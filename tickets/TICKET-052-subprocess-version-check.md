# TICKET-052: Subprocess test should also verify `--version` via `python3 -m fleet`

## Title
Extend the `python3 -m fleet` subprocess test to also assert `--version` output.

## Evidence
- `tests/test_cli.py::test_python_m_fleet_help_exits_zero` (added in Cycle 13,
  TICKET-051) runs `python3 -m fleet --help` as a subprocess and asserts
  returncode==0 and that "status" appears in stdout.
- The `--version` flag is tested only in-process (via `cli.main(["--version"])`
  with `capsys`), not via the `python3 -m fleet` path. A regression in
  `__main__.py` that breaks `sys.exit(main())` for `--version` specifically
  (e.g. a swallowed SystemExit) would not be caught by the subprocess test.

## Impact
- Low. The `--version` path goes through the same `main()` call as `--help`,
  so a break in one almost certainly breaks the other. But the subprocess
  path is the one that exercises `sys.exit()` in `__main__.py`, and
  `--version` raises `SystemExit(0)` from argparse (not a plain return),
  making it a slightly different code path through `sys.exit()`.

## Suggestion
- Add a second subprocess test (or extend the existing one) that runs
  `python3 -m fleet --version` and asserts returncode==0 and that stdout
  contains `fleet 0.1.0` (matching `fleet.__version__`).
