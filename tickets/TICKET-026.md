# TICKET-026 — `--json` intentionally not provided (documented)

**Phase:** CLI + Snapshot, part 2
**Status:** DONE (Cycle 6)

## Problem
The briefing offered an optional `--json` flag for `status`/`diff`
(machine-readable output) "only if clearly warranted and fully tested;
otherwise leave the CLI untouched."

## Decision
**Not added — documented as intentionally deferred.** There is no concrete
consumer that needs machine-readable output, and the data model
(`ProjectHealth` / `DiffRow`) would serialize trivially if one appears. Adding
an untested, unconsumed flag would violate the "only if clearly warranted and
fully tested" bar.

## Change
- Added a "Design notes" line to the `fleet/cli.py` module docstring recording
  that `--json` is intentionally not provided yet and why.
- No parser change.

## Tests
None (no behavior change).
