# TICKET-018: tests/test_snapshot.py — snapshot_diff added/removed/changed/unchanged classification

## Title
`fleet/snapshot.py` `snapshot_diff(snapshot, current)` is the core diff engine
that classifies each project as `added` / `removed` / `changed` / `unchanged`,
but it has no test. Every one of the four classification branches is untested.

## Evidence
- `fleet/snapshot.py:123` — `snapshot_diff` builds `snap_by_name` / `cur_by_name`
  and, for the union of names (sorted, line 135), emits:
    - `added` when `in_cur and not in_snap` (lines 138-139)
    - `removed` when `in_snap and not in_cur` (lines 140-141)
    - `changed` when `_field_changes(s, c)` is non-empty (lines 145-147)
    - `unchanged` otherwise (lines 148-149)
- `tests/test_snapshot.py` — only covers `save_snapshot`/`load_snapshot`
  round-trip (3 tests). No call to `snapshot_diff` anywhere in `tests/`.

## Impact
A regression in the set-difference logic (e.g. inverting the added/removed
conditions, dropping a project from the union, or mis-sorting rows) would
silently produce a wrong diff table with no test to catch it. The `changed`
vs `unchanged` boundary is the most error-prone seam and is entirely
unpinned.

## Suggestion
Add tests to `tests/test_snapshot.py` (or a new `tests/test_snapshot_diff.py`)
that build a `Snapshot` and a `current` list of `ProjectHealth` and assert:
- a project in `current` but not the snapshot yields `status == "added"`,
  `detail == "new project"`;
- a project in the snapshot but not `current` yields `status == "removed"`,
  `detail == "no longer discovered"`;
- a project present in both with an identical field set yields
  `status == "unchanged"`;
- a project present in both with one differing field yields
  `status == "changed"`;
- rows are returned sorted by `name` (assert the ordering of the returned
  `list[DiffRow]`).
