# TICKET-060: fleet/report.py — opt-in `Git` column in `render_portfolio`

## Title
Add an optional `git_states` parameter to `render_portfolio` so the status
table can render a 7th `Git` column (work-in-flight summary). Backward
compatible: `git_states=None` (default) yields byte-identical 6-column output.

## Evidence
- `fleet/report.py` `render_portfolio(healths: list[ProjectHealth]) -> str`
  (line 47) renders exactly 6 columns:
  `Project | Last Cycle | Last Outcome | Days Since Activity | Open Issues | Health`.
  The header (line 62), separator (line 63), and no-projects row (line 66)
  are all 6-column.
- `render_portfolio` does NOT import anything from `fleet.gittest`.
- The `Last Outcome` column is ALREADY rendered from
  `ProjectHealth.last_outcome` via `_fmt_outcome` (line 71) — so the only NEW
  column this cycle is `Git` (the briefing's ground truth). Do NOT add a second
  outcome column.
- `fleet/gittest.py` defines `GitState(unmerged_build_branches, unpushed_commits)`
  and `EMPTY_STATE = GitState((), 0)` — the input type for the new column.

## Change
In `fleet/report.py`:
- Add `from fleet.gittest import EMPTY_STATE, GitState`.
- Change the signature to `render_portfolio(healths, git_states=None)`.
- When `git_states is None`: keep the EXACT current 6-column header/separator/
  no-projects row and row format (byte-identical).
- When `git_states` is a dict: append a 7th `Git` column at the END of each row
  (after Health). Header gains ` Git |`, separator gains `---|`, no-projects row
  gains ` - |`. The Git cell is `_fmt_git(git_states.get(h.name, EMPTY_STATE))`.
- Add module helper `_fmt_git(gs: GitState) -> str`:
  - if `not gs.unmerged_build_branches and gs.unpushed_commits == 0`: return `"-"`.
  - else build parts: `unmerged:` + `+`.join(branches) (if any);
    `unpushed:` + str(count) (if > 0); return `",".join(parts)`.
- Pinned examples: `GitState((), 0)` -> `"-"`;
  `GitState(("build42/x",), 0)` -> `"unmerged:build42/x"`;
  `GitState((), 3)` -> `"unpushed:3"`;
  `GitState(("build42/x", "build43/y"), 3)` -> `"unmerged:build42/x+build43/y,unpushed:3"`.

Do NOT change `_sort_key`, `_fmt_days`, `_fmt_cycle`, `_fmt_outcome`, or the
existing 6-column rendering.
