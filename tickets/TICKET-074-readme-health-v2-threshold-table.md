# TICKET-074: Document the Health v2 threshold table in the README

## Title
The README documents only the v1 health table (`active`/`stalled`/`dead`).
Add a **Health classification (v2)** section documenting the four-class,
git-aware scheme, the most-severe-wins rule, the `max_steps_reached`-only
in-flight rule, and the v1/v2 30-day boundary divergence.

## Evidence
- `README.md` (pre-change) — a single "Health classification" section with a
  three-row v1 table; no mention of `stranded`/`paused`, the `Git` column,
  `--filter stranded|paused`, the `health_v2` snapshot field, or the 30-day
  divergence.
- `fleet/health.py` — `classify_health_v2(days, last_outcome, git_state)` is
  the four-class, most-severe-wins classifier (`stranded` > `active` >
  `paused` > `dead`); only the exact outcome `max_steps_reached` counts as
  "work in flight".
- `fleet/health.py` — `DEAD_MIN_DAYS = 30` (v2 dead is `>= 30`) vs
  `STALLED_MAX_DAYS = 30` (v1 dead is `> 30`); the two intentionally disagree
  at exactly 30 days (pinned by tests in Cycles 15/17; see TICKET-059).

## Change
- Rename the existing section to **Health classification (v1)** and keep the
  v1 table.
- Add **Health classification (v2)** with a four-row table:
  - `stranded` — unmerged `build*` branch OR unpushed commits on `main`,
    regardless of recency.
  - `active` — touched ≤ 7 days AND work in flight (last outcome
    `max_steps_reached`; an unmerged branch already → `stranded`).
  - `paused` — recently touched but done, or idle in the 8-29 day band with
    nothing in flight.
  - `dead` — 30+ days untouched (or no activity signal) with nothing in
    flight.
- State the most-severe-wins rule and that only `max_steps_reached` counts as
  in-flight.
- Add a callout documenting the v1/v2 30-day boundary divergence (v1 `> 30`,
  v2 `>= 30`; not unified; do not normalize).

## Acceptance
- README documents all four v2 classes, the most-severe-wins rule, the
  `max_steps_reached`-only in-flight rule, and the v1/v2 30-day divergence.
- The v1 table is preserved.
