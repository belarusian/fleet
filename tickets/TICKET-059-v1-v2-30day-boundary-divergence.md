# TICKET-059: document the v1/v2 30-day boundary divergence (stalled vs dead)

## Title
Document (and intentionally preserve) the fact that the v1 and v2 classifiers
disagree at exactly 30 days: v1 `classify_health` calls 30 days "stalled"
(31+ is "dead"), while v2 `classify_health_v2` calls 30 days "dead" (29 is
"paused"). This is by design, not a bug — but it must be documented so a
future maintainer does not "fix" one to match the other.

## Evidence
- v1 `classify_health` (`fleet/health.py` lines 183-199) uses:
  `if days <= ACTIVE_MAX_DAYS (7): active` / `if days <= STALLED_MAX_DAYS (30):
  stalled` / `return dead`. So **30 days -> "stalled"**, 31 days -> "dead".
  Pinned by `tests/test_health.py::test_classify_health_boundaries`
  (`classify_health(30, True) == "stalled"`, `classify_health(31, True) == "dead"`)
  and `test_assess_stalled_dead_boundary` (30 -> stalled, 31 -> dead).
- v2 `classify_health_v2` (TICKET-055) uses `old = days is not None and
  days >= DEAD_MIN_DAYS (30)`. So **30 days -> "dead"** (when nothing in
  flight), 29 days -> "paused". Pinned by acceptance case 14
  ("30d, nothing in flight -> dead; 29d, nothing in flight -> paused").
- The two schemes therefore diverge at the single point `days == 30`:
  v1 = "stalled", v2 = "dead". The v1 boundary is `> 30` for dead; the v2
  boundary is `>= 30` for dead.

## Impact
Low severity, documentation-only. Both behaviors are correct for their own
scheme and both are pinned by tests. The risk is a future edit that "normalizes"
the two (e.g. changing `DEAD_MIN_DAYS` to 31, or changing v2 to `> DEAD_MIN_DAYS`)
to make them agree, which would silently break the v2 acceptance cases (14) and
the Cycle 17 canaries.

## Suggestion
- Do NOT change either boundary. Keep v1 at `> STALLED_MAX_DAYS` and v2 at
  `>= DEAD_MIN_DAYS`.
- Add a one-line note in the v2 docstring (see TICKET-058) and/or a comment
  at the `DEAD_MIN_DAYS` constant: "v2 dead boundary is `>= 30`; v1 dead
  boundary is `> 30` — intentionally different, do not unify."
- Optionally add a comment in `tests/test_health.py` near the v2 boundary test
  (case 14) noting the deliberate divergence from the v1 30-day test.
- Gate: `pytest tests/ -x -q`, `ruff check fleet/`,
  `mypy fleet/ --ignore-missing-imports`.
