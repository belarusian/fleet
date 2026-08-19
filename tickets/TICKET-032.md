# TICKET-032 — Robustness: unparseable gate log (no cycle headers) → empty GateLog → dead

**Phase:** Cycle 8 synthesis audit
**Status:** RESOLVED (test added)

## Problem
A project whose gate log file contains **garbage** (no `## Cycle N` headers,
no `## Build Order` table) was not covered by a test. The behavior is correct
but was unverified: such a file parses to an empty `GateLog`, and `assess`
must classify the project as `dead` with all-`None` cycle metrics.

## Evidence
- `fourseer/parse/gate_log.py:_parse_cycle_blocks`: only lines matching
  `_CYCLE_HEADER_RE` (`^##\s+Cycle\s+(\d+)`) open a block; a file with no such
  line yields `[]`.
- `fourseer/parse/gate_log.py:_parse_build_order`: only lines after a
  `## Build Order` header are scanned; absent → `[]`.
- Probed: `assess` on a gate log of `"this is not markdown at all\n### no
  cycle headers here\n"` → `health="dead"`, `last_cycle=None`,
  `last_outcome=None`, `days_since_activity=0`.

## Impact
Without a test, a change to the cycle-header regex or the build-order scanner
that mis-fires on non-matching prose would go undetected.

## Suggestion
Add `test_assess_unparseable_gate_log` to `tests/test_robustness.py`.

## Tests
- Added: `test_assess_unparseable_gate_log` in `tests/test_robustness.py`.
