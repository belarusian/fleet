# TICKET-073: Bump the shipped version to 0.2.0 (Health v2 release)

## Title
Move `fleet` from `0.1.0` to `0.2.0` consistently across the version string,
the packaging metadata, and the hard-coded version test, so the Health v2 arc
(Cycles 14-18) ships as the second release.

## Evidence
- `fleet/__init__.py:23` — `__version__ = "0.1.0"`.
- `pyproject.toml:7` — `version = "0.1.0"` (the `[project]` version, not the
  `ruff>=0.1.0` dev pin on line 18, which is unrelated and must not change).
- `tests/test_cli.py:586-588` — `test_cli_version_is_0_1_0` hard-asserts
  `__version__ == "0.1.0"`. The two sibling version tests
  (`test_cli_version_flag_exits_zero_and_prints_version`,
  `test_cli_version_flag_prints_exact_version`) are dynamic (they compare
  against `__version__`) and need no change.

## Change
- `fleet/__init__.py`: `__version__ = "0.2.0"`.
- `pyproject.toml`: `version = "0.2.0"`.
- `tests/test_cli.py`: rename `test_cli_version_is_0_1_0` to
  `test_cli_version_is_0_2_0`, assert `__version__ == "0.2.0"`, and update the
  docstring to "second release / Health v2".

## Acceptance
- `fleet.__version__ == "0.2.0"` and `pyproject.toml` `version == "0.2.0"`.
- `python3 -m fleet --version` prints exactly `fleet 0.2.0` and exits 0.
- `test_cli_version_is_0_2_0` passes; the two dynamic version tests stay green.
- Gate: `pytest tests/ -x -q`, `ruff check fleet/`,
  `mypy fleet/ --ignore-missing-imports`.
