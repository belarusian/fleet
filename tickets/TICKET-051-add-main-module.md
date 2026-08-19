# TICKET-051: Add fleet/__main__.py so `python3 -m fleet` works

## Title
Make `python3 -m fleet` a working entrypoint by adding `fleet/__main__.py`
delegating to `fleet.cli:main`.

## Evidence
- `python3 -m fleet` currently fails: `can't find package 'fleet'`
  module resolution succeeds but `No module named fleet.__main__` /
  `"fleet" __main__ not found`-style error — there is no `fleet/__main__.py`
  in the package (only `__init__.py`, `cli.py`, `discover.py`, `health.py`,
  `report.py`, `snapshot.py`).
- `fleet/cli.py` already exposes `main()`, and the `fleet` console script
  (pyproject `[project.scripts]`) already delegates to `fleet.cli:main`.
  The `__main__` module is the only missing path for invoking the same CLI
  without installation.

## Change
- `fleet/__main__.py` (new): delegate to the existing CLI entrypoint:
  - `from fleet.cli import main`
  - `if __name__ == "__main__": sys.exit(main())`
  Nothing else; do NOT reimplement argument parsing.
- `tests/test_cli.py` (or `tests/test_main_module.py`): 1 new test
  `test_python_m_fleet_help_exits_zero` that runs
  `python3 -m fleet --help` as a subprocess and asserts returncode == 0 and
  the help text mentions the `status` subcommand. Must not depend on CWD or
  `~/AI`; run from a neutral directory (e.g. `tmp_path`) so it exercises real
  package resolution, not the ambient cwd.

## Acceptance
- `python3 -m fleet --help` exits 0 from an arbitrary directory.
- `python3 -m fleet --version` still prints `fleet 0.1.0` (delegation reaches
  the same parser, including the `--version` flag from Cycle 12).
- Full gate green: `pytest tests/ -x -q`, `ruff check fleet/`,
  `mypy fleet/ --ignore-missing-imports`.
