# TICKET-065: assess() never calls classify_health_v2, so the target pipeline's middle link is dead

## Title
`assess` (the pipeline's middle link) produces only a v1 health; v2 is unreachable from it.

## Evidence
- `fleet/health.py:324` — `assess` computes `health = classify_health(days, has_traj)` (v1,
  3 classes). It never calls `classify_health_v2` and never reads git state.
- `fleet/health.py:15-16` — the module docstring states v2 is "a pure function, not yet wired
  into :func:`assess`".
- `ProjectHealth` (fleet/health.py:57-78) has a single `health: str` field holding the v1 class.
  There is no field for a v2 class, so `assess` cannot even carry a v2 result forward.
- The only caller of `classify_health_v2` in the whole codebase is `fleet/cli.py:135`, inside
  the `--filter stranded|paused` branch.

## Impact
The target pipeline `assess -> classify_health_v2(read_gitstate(...))` cannot be satisfied by
`assess` as written: `assess` does not produce the inputs a composed v2 call would need in one
object, and it does not produce a v2 class at all. Any test claiming to verify the pipeline
through `assess` is actually verifying v1. This is the root reason TICKET-064's composed path
does not exist.

## Suggestion
This is a TEST-ONLY cycle, so do not change `assess`. Instead, file a follow-up (non-test)
ticket to decide the integration shape: either (a) add a `health_v2: str` field to
`ProjectHealth` and have `assess` accept an optional `git_state` to compute it, or (b) keep v2
as a pure post-processing step applied by the CLI/report layer. Until that decision is made,
integration tests must compose the links manually (see TICKET-064) rather than route through
`assess`.
