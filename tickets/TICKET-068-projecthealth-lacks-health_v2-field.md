# TICKET-068: ProjectHealth has no health_v2 field, so the v2 snapshot shape cannot be carried

## Title
`ProjectHealth` (the snapshot's per-project row) has no `health_v2` field; the v2 snapshot
shape requires a defaulted `health_v2: str | None` field.

## Evidence
- `fleet/health.py:57-85` — `ProjectHealth` is a frozen dataclass with exactly seven fields:
  `name`, `last_cycle`, `last_outcome`, `days_since_activity`, `open_issues`, `health`,
  `last_activity`. There is no `health_v2` field.
- `fleet/health.py:73-74` — the single `health: str` field holds the v1 class only
  (`"active"` / `"stalled"` / `"dead"`), produced by `classify_health` at `fleet/health.py:324`.
- `fleet/health.py:228` — `classify_health_v2(days, last_outcome, git_state)` exists and returns
  one of `stranded` / `active` / `paused` / `dead`, but its result is never stored on
  `ProjectHealth`; the only caller is the CLI `--filter` branch (`fleet/cli.py:135`).
- `fleet/snapshot.py:34-45` — `_health_to_dict` serializes exactly the seven fields above; there
  is no `health_v2` key, so even if a v2 class were computed it could not be persisted.

## Impact
The v2 snapshot format cannot be expressed: a snapshot row cannot carry a v2 class, so
`save_snapshot` has nothing to round-trip and `_field_changes` has nothing to diff. This is the
root prerequisite for the v2 snapshot shape (see TICKET-069/070/071).

## Suggestion
Add a defaulted field to `ProjectHealth`:
  `health_v2: str | None = None`
Placed after `last_activity` (or as the last field) so existing positional constructions in
`assess` (`fleet/health.py:327-335`) and in tests keep working unchanged. Defaulting to `None`
is what lets old snapshots (which lack the key) still load — see TICKET-072. Update the
`ProjectHealth` docstring (fleet/health.py:58-78) to document the new field.
