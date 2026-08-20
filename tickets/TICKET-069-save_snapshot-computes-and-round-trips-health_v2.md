# TICKET-069: save_snapshot does not accept git_states, so it cannot compute or persist health_v2

## Title
`save_snapshot(healths, path)` has no `git_states` parameter, never calls
`classify_health_v2`, and `_health_to_dict`/`_health_from_dict` do not round-trip a
`health_v2` key.

## Evidence
- `fleet/snapshot.py:65` — signature is `save_snapshot(healths: list[ProjectHealth], path: str | Path) -> Path`.
  There is no `git_states` parameter, so the function has no access to the git-side signal that
  `classify_health_v2` requires.
- `fleet/snapshot.py:71-74` — the document body is built purely from
  `[_health_to_dict(h) for h in healths]`; `classify_health_v2` is never imported or called in
  `fleet/snapshot.py` (grep for `classify_health_v2` / `git_states` in that file returns nothing).
- `fleet/snapshot.py:34-45` — `_health_to_dict` emits seven keys and omits `health_v2`.
- `fleet/snapshot.py:47-63` — `_health_from_dict` reads seven keys and omits `health_v2`, so a
  v2 class could not survive a save->load round-trip even if it were written.
- `fleet/health.py:228` — `classify_health_v2(days, last_outcome, git_state)` is the pure function
  that must be invoked per project to derive the v2 class.

## Impact
The v2 snapshot shape is not produced: saved snapshots contain only v1 data, so a later
`load_snapshot` + `snapshot_diff` cannot observe any v2 transition. This is the central item of the
v2 snapshot work and depends on TICKET-068 (the field to store the result in).

## Suggestion
Change the signature to `save_snapshot(healths, path, git_states: dict[str, GitState] | None = None)`.
When `git_states` is provided, compute each row's v2 class as
`classify_health_v2(h.days_since_activity, h.last_outcome, git_states.get(h.name, EMPTY_STATE))`
and attach it to the row (via the `health_v2` field from TICKET-068) before serializing. Add
`"health_v2": h.health_v2` to `_health_to_dict` and `health_v2=d.get("health_v2")` to
`_health_from_dict` so the value round-trips. Defaulting `git_states=None` preserves the existing
call shape (see TICKET-071 for the CLI wiring).
