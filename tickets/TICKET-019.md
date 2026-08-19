# TICKET-019: tests/test_snapshot.py — _field_changes per-field change detection

## Title
`fleet/snapshot.py` `_field_changes(s, c)` is the helper that decides *which*
tracked fields differ between two `ProjectHealth` rows and renders each as a
`"old->new"` string. It is private but is the entire basis of the `changed`
detail text, and it has no test.

## Evidence
- `fleet/snapshot.py:153` — `_field_changes` compares exactly four fields and
  appends a formatted change string for each that differs:
    - `last_cycle`   -> `"cycle {s}->{c}"`
    - `last_outcome` -> `"outcome {s}->{c}"`
    - `health`       -> `"health {s}->{c}"`
    - `open_issues`  -> `"issues {s}->{c}"`
  It deliberately does NOT compare `days_since_activity` or `last_activity`.
- `tests/` — no test references `_field_changes` or asserts on the `detail`
  string of a `changed` `DiffRow`.

## Impact
A regression (e.g. comparing the wrong field, a typo in the `old->new` format,
or accidentally including `days_since_activity`) would corrupt the human-readable
diff detail with no test to catch it. The intentional exclusion of
`days_since_activity`/`last_activity` is a design decision that is currently
unpinned and could silently drift.

## Suggestion
Add tests that call `_field_changes` (or `snapshot_diff` and inspect `detail`)
with two `ProjectHealth` rows that differ in:
- each single field in isolation (cycle, outcome, health, issues) -> assert the
  exact `detail` string;
- multiple fields at once -> assert all change fragments appear, comma-joined;
- no differing field -> assert an empty list / `unchanged`;
- a row that differs ONLY in `days_since_activity` or `last_activity` -> assert
  it is reported as `unchanged` (pinning the intentional exclusion).
