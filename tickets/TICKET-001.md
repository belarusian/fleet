# TICKET-001: discover.py — No guard against empty or missing trajectory directory

## Title
Discovery returns empty/None silently when trajectory root does not exist or contains zero entries.

## Evidence
`fleet/discover.py` — the function that walks the trajectory root (e.g. `list_trajectories()` or equivalent) performs a `glob`/`os.listdir` on a path that may not exist. There is no explicit check:
- `os.path.isdir(root)` before listing
- A sentinel return (empty list vs. `None`) is not documented or enforced
- No log line or warning is emitted when the directory is absent

Callers in `fleet/health.py` then iterate over the result without a `if not trajectories:` guard, so a missing root propagates as an empty metric set rather than a visible error.

## Impact
- A misconfigured `TRAJECTORY_ROOT` env var or a fresh clone with no data produces a health report that looks "all green / zero activity" instead of failing loudly.
- Downstream consumers (dashboard, alerting) cannot distinguish "no trajectories yet" from "trajectories were deleted / path is wrong."
- Silent data loss in audit trails: the cycle completes, writes a health snapshot, and the operator never notices the root was wrong.

## Suggestion
1. At the top of the discovery entry-point, add: