# TICKET-017: tests/test_snapshot.py — snapshot save/load round-trip

## Title
`fleet/snapshot.py` `save_snapshot`/`load_snapshot` round-trips a
`ProjectHealth` list to/from JSON, but there is no test that the round-trip
preserves every field (especially that `last_activity` survives as a
`datetime` and that `None` fields stay `None`).

## Evidence
- `fleet/snapshot.py` — `_health_to_dict` serializes `last_activity` via
  `.isoformat()` (or `None`); `_health_from_dict` rebuilds it via
  `datetime.fromisoformat` (or `None`). `save_snapshot`/`load_snapshot` wrap
  these.
- `tests/` — no `test_snapshot.py` exists.

## Impact
A serialization bug (e.g. dropping `last_activity`, coercing `None` to a
string, or losing the timezone) would silently corrupt saved snapshots and
break the later `diff` phase, with no test to catch it.

## Suggestion
Add `tests/test_snapshot.py` that builds a `ProjectHealth` list with one fully
populated row (datetime `last_activity`) and one with `None` fields, writes it
with `save_snapshot`, reads it back with `load_snapshot`, and asserts every
field is preserved, `last_activity` is a `datetime` equal to the original, and
the `None` fields remain `None`.
