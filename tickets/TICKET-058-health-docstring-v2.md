# TICKET-058: fleet/health.py — module docstring must document the v2 four-class scheme

## Title
Update the `fleet/health.py` module docstring so it documents BOTH the v1
three-class scheme (active/stalled/dead, used by `assess`) and the v2
four-class scheme (stranded/active/paused/dead, used by `classify_health_v2`),
plus the new `DEAD_MIN_DAYS` constant.

## Evidence
- The module docstring (`fleet/health.py` lines 1-11) documents only the v1
  scheme:
    - ``active``  — ran within 7 days
    - ``stalled`` — 8-30 days
    - ``dead``    — more than 30 days, or no trajectories at all
- After TICKET-055, `fleet/health.py` will also expose `classify_health_v2`
  (four classes) and the `DEAD_MIN_DAYS = 30` constant, but the module
  docstring will still describe only the v1 three-class scheme. A reader of the
  module docstring would not learn that a second, four-class classifier exists.

## Change
- Rewrite the module docstring to present both schemes side by side:
  - v1 — `classify_health` (used by `assess`): active / stalled / dead by days
    since last activity.
  - v2 — `classify_health_v2` (a pure function, not yet wired into `assess`):
    four classes, most-severe-wins (stranded > active > paused > dead), with a
    one-line definition of each class.
- Note the deliberate boundary divergence: the v2 dead boundary is
  `days >= DEAD_MIN_DAYS` (>= 30) while the v1 dead boundary is
  `days > STALLED_MAX_DAYS` (> 30); they intentionally disagree at exactly 30
  days and must not be unified (see TICKET-059).

## Acceptance
- The module docstring names both `classify_health` and `classify_health_v2`,
  lists all four v2 classes, and states the v1/v2 30-day boundary divergence.
- Gate green: `pytest tests/ -x -q`, `ruff check fleet/`,
  `mypy fleet/ --ignore-missing-imports`.
