# TICKET-050: Add tests pinning the version string and `fleet --version`

## Title
Tests that pin `fleet.__version__` and that `fleet --version` exits 0 and prints it.

## Evidence
- `fleet/__init__.py` defines `__version__ = "0.1.0"`; `pyproject.toml` has
  `version = "0.1.0"`. This is the first release, so `0.1.0` is warranted — no
  bump.
- Before this change there was no test pinning the version or the `--version`
  flag behavior.

## Change
- `tests/test_cli.py`: 3 new tests (import `__version__` from `fleet`):
  1. `test_cli_version_flag_exits_zero_and_prints_version` — `cli.main(["--version"])`
     raises `SystemExit` with code 0 and stdout contains `__version__`.
  2. `test_cli_version_flag_prints_exact_version` — stdout is exactly
     `f"fleet {__version__}"` (pins the string so a silent bump is caught).
  3. `test_cli_version_is_0_1_0` — `__version__ == "0.1.0"`.
- Uses `pytest.raises(SystemExit)` + `capsys` (argparse `--version` writes to
  stdout, not stderr). No CWD or `~/AI` dependency.

## Acceptance
- All 3 tests pass; the existing guard tests stay intact.
- A silent version bump in `fleet/__init__.py` is caught by the exact-string test.
