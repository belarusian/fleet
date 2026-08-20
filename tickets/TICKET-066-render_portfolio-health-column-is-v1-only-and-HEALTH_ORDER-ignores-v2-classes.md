# TICKET-066: render_portfolio's Health column is v1-only; _HEALTH_ORDER ignores v2 classes

## Title
The rendered table's Health column and its sort tie-break only understand v1 classes, so a v2
class can never be displayed or ordered.

## Evidence
- `fleet/report.py:20` — `_HEALTH_ORDER = {"active": 0, "stalled": 1, "dead": 2}`. It has no
  entry for the v2-only classes `stranded` or `paused`.
- `fleet/report.py:69` — the sort tie-break uses `_HEALTH_ORDER.get(h.health, 3)`. A row whose
  `health` were `stranded` or `paused` would fall to the default `3` (after `dead`), which is
  the wrong severity order (stranded is the MOST severe, not the least).
- `render_portfolio` renders `h.health` verbatim (fleet/report.py:117). Since `assess` only ever
  stores a v1 class (see TICKET-065), the Health column can never show a v2 class.
- No test in `tests/test_report.py` constructs a `ProjectHealth` with `health="stranded"` or
  `health="paused"` and checks the rendered cell or the sort order.

## Impact
If a future change (TICKET-065) starts storing a v2 class on `ProjectHealth`, the table would
render it but sort it to the bottom (severity 3), silently mis-ordering the most-severe
(stranded) projects. There is no test pinning the intended v2 ordering, so this would ship
undetected.

## Suggestion
Decide the display contract for v2 classes in the Health column, then:
1. extend `_HEALTH_ORDER` to include `stranded` and `paused` in the correct severity order
   (stranded most severe, then active, then paused, then dead — matching the v2
   most-severe-wins ordering in fleet/health.py:22-28), and
2. add a `tests/test_report.py` case that builds rows with `health="stranded"` /
   `health="paused"` and asserts both the rendered cell and the sort position.
