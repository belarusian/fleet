# TICKET-025 — `diff` is unfiltered by design (documented)

**Phase:** CLI + Snapshot, part 2
**Status:** DONE (Cycle 6)

## Problem
The briefing offered two options for `--filter` on `diff`: add it (filter diff
rows by resulting health) or document that diff is unfiltered by design.

## Decision
**Documented as unfiltered by design.** A health filter does not map cleanly
onto diff rows: `removed` rows have no resulting health (the project is gone),
and `added`/`changed` rows carry the *current* health, so filtering would hide
part of the change set. The health view of the *current* state is already
available via `status --filter`.

## Change
- Added a "Design notes" section to the `fleet/cli.py` module docstring
  explaining why `diff` is unfiltered and pointing users to `status --filter`.
- No parser change; `diff` keeps its `--root`/`--snapshot` args only.

## Tests
No new tests required (no behavior change); existing `diff` tests continue to
cover the full unfiltered change set (added/removed/changed/unchanged).
