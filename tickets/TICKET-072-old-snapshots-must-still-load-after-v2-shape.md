# TICKET-072: old (v1) snapshots must still load after the v2 shape is added

## Title
When `health_v2` is added to the snapshot shape, pre-existing v1 snapshots (which lack the
`health_v2` key) must still load without error and must not be misreported as changed.

## Evidence
- `fleet/snapshot.py:47-63` — `_health_from_dict` currently reads keys with `.get(...)` defaults
  (`open_issues=d.get("open_issues", 0)`, `health=d.get("health", "dead")`), which is the existing
  pattern for tolerating absent keys. A new `health_v2=d.get("health_v2")` read would default to
  `None` for old snapshots, which is the correct "no v2 recorded" value.
- `fleet/snapshot.py:153-165` — `_field_changes` compares fields directly. If a freshly-assessed
  current row always has a computed `health_v2` (non-None) but a loaded old-snapshot row has
  `health_v2=None`, a naive comparison would flag every project as `changed` with a
  `health_v2 - -><class>` fragment on the first diff after the upgrade — a spurious change storm.
- `tests/test_snapshot.py` — round-trip tests build rows via `ProjectHealth(...)`; there is no test
  that loads a hand-written v1 JSON (no `health_v2` key) and asserts it loads with
  `health_v2 is None`.

## Impact
Two risks: (1) a load-time crash or `KeyError` if the new field is read with `d["health_v2"]`
instead of `.get`; (2) a false "changed" diff for every project the first time a v1 snapshot is
compared against a v2-assessed portfolio, because `None != <class>`. Both would make the v2
upgrade look like a mass regression.

## Suggestion
- In `_health_from_dict`, read `health_v2=d.get("health_v2")` (default `None`) — never `d["health_v2"]`.
- Decide and pin the diff semantics for the `None -> <class>` case: either (a) treat a
  `None`-on-snapshot side as "not comparable" and suppress the fragment, or (b) accept the one-time
  fragment and document it. Whichever is chosen, add a regression test that loads a v1 JSON
  (no `health_v2` key), asserts `health_v2 is None`, and asserts the diff behavior matches the
  chosen semantics.
