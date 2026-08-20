# TICKET-070: _field_changes does not surface a health_v2 <a>-><b> fragment

## Title
`_field_changes` compares only `last_cycle`, `last_outcome`, `health`, and `open_issues`; it never
emits a `health_v2` fragment, so a v2-class transition is invisible in the diff.

## Evidence
- `fleet/snapshot.py:153-165` — `_field_changes` builds `changes` from exactly four comparisons:
  `last_cycle` (line 156), `last_outcome` (line 158), `health` (line 160), `open_issues` (line 162).
  There is no `health_v2` comparison.
- `fleet/snapshot.py:160-161` — the v1 fragment is `f"health {s.health}->{c.health}"`; the v2
  fragment must be analogous but must render `None` as `-` (e.g. `health_v2 -->stranded`), which
  the existing `health` fragment does not do (v1 `health` is never `None`).
- `tests/test_snapshot.py` — `test_field_changes_all_four_fields` pins the exact four-fragment
  list; adding a fifth `health_v2` fragment will require updating this test and the
  `test_snapshot_diff_multiple_fields` expected string.

## Impact
Even after TICKET-068/069 persist `health_v2`, a diff between two snapshots will not report a
v2-class change (e.g. `paused -> stranded`), so the v2 snapshot's purpose — surfacing v2
transitions — is not met.

## Suggestion
In `_field_changes`, after the `health` comparison, add:
  `if s.health_v2 != c.health_v2: changes.append(f"health_v2 {s.health_v2 or '-'}->{c.health_v2 or '-'}")`
so a `None` value renders as `-`. Update `tests/test_snapshot.py` (`test_field_changes_all_four_fields`
and `test_snapshot_diff_multiple_fields`) to include the new fragment, and add a dedicated case for
the `None -> class` (`- -> ...`) rendering.
