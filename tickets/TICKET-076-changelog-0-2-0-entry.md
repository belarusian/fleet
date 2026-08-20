# TICKET-076: Add a [0.2.0] CHANGELOG entry covering the Health v2 arc

## Title
`CHANGELOG.md` has a single `[0.1.0]` entry. Add a `## [0.2.0]` section above
it that records the Health v2 arc (Cycles 14-18) as the second release,
leaving `[0.1.0]` intact.

## Evidence
- `CHANGELOG.md` (pre-change) — only `## [0.1.0] - 2026-08-19`.
- The Health v2 arc landed across Cycles 14-18: `fleet.gittest`
  (`read_gitstate`/`GitState`/`EMPTY_STATE`), `classify_health_v2`,
  `ProjectHealth.health_v2`, the report `Git` column, the CLI
  `--filter stranded|paused`, snapshot v2 (`health_v2` round-trip + diff
  fragment + old-snapshot loading), and the end-to-end v2 integration test.

## Change
- Add `## [0.2.0] - <date>` above `[0.1.0]` with a summary paragraph (four
  classes, most-severe-wins, `max_steps_reached`-only in-flight, v1/v2 30-day
  divergence) and an **Added** list covering:
  - `fleet.gittest` — `read_gitstate` / `GitState` / `EMPTY_STATE`.
  - `fleet.health.classify_health_v2` — four-class, most-severe-wins.
  - `ProjectHealth.health_v2` — defaulted field.
  - Report — opt-in `Git` column.
  - CLI — `Git` column always shown; `--filter` accepts `stranded`/`paused`.
  - Snapshot v2 — `save_snapshot(..., git_states=...)` stores `health_v2`;
    `snapshot_diff` surfaces a `health_v2 <a>-><b>` fragment; old v1 snapshots
    still load.
  - Integration — end-to-end v2 pipeline test + live-root smoke test.
- Keep the existing `[0.1.0]` entry byte-for-byte intact.

## Acceptance
- `CHANGELOG.md` has a `[0.2.0]` entry covering the Health v2 arc; `[0.1.0]`
  is unchanged.
