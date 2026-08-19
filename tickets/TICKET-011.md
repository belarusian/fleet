# TICKET-011: health.py / README.md — "30+ days" dead threshold is misstated

## Title
The documented dead threshold ("30+ days") contradicts the code, which classifies a project idle exactly 30 days as `stalled`, not `dead`.

## Evidence
- `fleet/health.py:24` — `STALLED_MAX_DAYS = 30`.
- `fleet/health.py:195-198` — `if days <= ACTIVE_MAX_DAYS: return "active"` / `if days <= STALLED_MAX_DAYS: return "stalled"` / `return "dead"`. So `days == 30` → `stalled`; `days == 31` → `dead`.
- `fleet/health.py:10` (module docstring) — "``dead`` — 30+ days, or no trajectories at all".
- `fleet/health.py:186` (`classify_health` docstring) — "the project is 30+ days idle".
- `README.md:14` — "**dead** — 30+ days or no trajectories".

The new test `tests/test_health.py::test_assess_stalled_dead_boundary` pins the actual behavior: 30 days → `stalled`, 31 days → `dead`.

## Impact
- An operator reading the README or the module docstring believes a project idle 30 days is already `dead`, but the scanner reports it as `stalled`. The `fleet status --filter dead` output will not include a 30-day-idle project, surprising anyone who trusts the docs.
- The off-by-one is exactly the kind of boundary that is easy to get wrong and hard to spot without a test; the docs currently encode the wrong boundary.

## Suggestion
1. Change the wording in `fleet/health.py:10`, `fleet/health.py:186`, and `README.md:14` from "30+ days" to "more than 30 days" (or "31+ days") for the `dead` class, and keep "8-30 days" for `stalled`.
2. Keep the code as-is (the `<= STALLED_MAX_DAYS` boundary is the intended, tested behavior).
3. No code change required; this is a documentation correction.
