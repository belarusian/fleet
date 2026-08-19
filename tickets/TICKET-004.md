# TICKET-004: discover.py + health.py — `last_cycle` / `last_outcome` derivation is order-dependent and fragile

## Title
The "last cycle" and "last outcome" fields are derived by sorting trajectory filenames or by taking the last element of an unsorted list, making them incorrect when files are created out of order or when naming conventions change.

## Evidence
`fleet/discover.py` — trajectory discovery returns a list whose order depends on `os.listdir()` (arbitrary) or on a `sorted()` call that lexicographically sorts filenames. If filenames encode timestamps as `YYYYMMDD_HHMMSS`, lexicographic sort works; but:
- If the naming convention changes (e.g. to UUIDs or to `cycle_001`), the sort order no longer reflects chronology.
- `fleet/health.py` then takes `trajectories[-1]` as "last cycle" without verifying it is actually the most recent by internal timestamp.

Additionally, `last_outcome` is read from a field inside the trajectory file that may be written *after* the file is closed/flushed, so a concurrent read during a running cycle sees a partial/missing outcome.

## Impact
- Health report shows the wrong cycle as "last" when filenames don't sort chronologically (e.g. after a naming-convention migration or a manual file rename).
- `last_outcome` can be `None` or a stale value if the health check runs mid-cycle, leading to false "cycle failed" alerts.
- The bug is silent: no exception, no log — just a wrong number in the report.

## Suggestion
1. In `discover.py`, sort trajectories by their **internal** `started_at` / `cycle_id` field, not by filename. Expose a `TrajectoryRecord` dataclass with a `.started_at` attribute.
2. In `health.py`, derive `last_cycle` as `max(trajectories, key=lambda t: t.started_at)` and `last_outcome` only from trajectories whose `status == "completed"`.
3. Add a `"derived_from"` metadata field to the health report recording which trajectory ID was used, for auditability.
4. Add tests:
   - `test_last_cycle_uses_internal_timestamp_not_filename`
   - `test_last_outcome_ignores_incomplete_cycles`
   - `test_last_cycle_with_uuid_filenames`
