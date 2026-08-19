# TICKET-047 — tests/test_examples.py (example-validity test)

**Cycle:** 11 (Polish + Release, part 2)
**Type:** tests
**Status:** open

## Problem
Nothing pins that the `examples/` tree stays valid. If an example file is
edited into an unparseable shape, `fleet status --root examples/` would break
silently.

## Target
Add `tests/test_examples.py`:
- Locate the `examples/` dir relative to the repo
  (`Path(__file__).resolve().parent.parent / "examples"`).
- Run `discover` on it; assert the expected project names are all found.
- Run `assess` (pin the clock with the `datetime`-subclass trick used in
  `tests/test_health.py`) + `render_portfolio`; assert the table contains every
  project name and a header row.
- Do NOT assert specific health values (mtimes vary across checkouts) — assert
  discoverability + renderability + no crash.

## Constraints
- Must not depend on CWD (locate `examples/` via `__file__`).
- Must not touch the real `~/AI`.

## Acceptance
- `tests/test_examples.py` exists and passes.
- Gate green (pytest + ruff + mypy).
