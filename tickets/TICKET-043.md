# TICKET-043 — README "How it works" section

**Cycle:** 11 (Polish + Release, part 2)
**Type:** docs
**Status:** open

## Problem
`README.md` has no "How it works" section. A reader cannot see how the four
pipeline stages compose into the portfolio table. The only pipeline description
is the two-sentence intro paragraph.

## Target
Add a short "How it works" section (3-5 lines) describing the pipeline using
ONLY functions that exist:

1. `discover` (fleet/discover.py) scans the root for project `ai/` dirs at
   depth <= 2 that satisfy `is_project` (has trajectories or a gate log).
2. `assess` / `project_health` (fleet/health.py) extract per-project metrics via
   the `fourseer` parsers: last cycle, last outcome, days since activity, open
   issues.
3. `classify_health` (fleet/health.py) maps those to `active` / `stalled` / `dead`.
4. `render_portfolio` (fleet/report.py) emits the markdown table, sorted by
   last-activity desc (no-activity last).

## Constraints
- Do NOT invent functions that do not exist.
- Keep it consistent with the existing intro paragraph (do not contradict it).

## Acceptance
- README has a `## How it works` section naming the four real functions.
- Gate green (pytest + ruff + mypy).
