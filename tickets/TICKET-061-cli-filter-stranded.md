# TICKET-061: fleet/cli.py — `--filter stranded`/`paused` + source the git state

## Title
Extend the `status` subcommand to (a) accept the two v2-only filter classes
`stranded` and `paused` in addition to the v1 `active`/`stalled`/`dead`/`all`,
and (b) always render the `Git` column by sourcing a per-project `GitState`
via `read_gitstate`. The `health` column stays v1 (full v2 wiring is Cycle 17).

## Evidence
- `fleet/cli.py` `_VALID_FILTERS = ("active", "stalled", "dead", "all")`
  (line 49). `--filter` uses `choices=_VALID_FILTERS`.
- `_cmd_status` (line 116) currently does:
  `healths = _assess_all(args.root)`; if filter != "all" keep rows where
  `h.health == args.filter`; `print(report.render_portfolio(healths))`.
  It does NOT source any git state and does NOT pass `git_states` to
  `render_portfolio`.
- `fleet/cli.py` does NOT import `read_gitstate`, `EMPTY_STATE`, or
  `classify_health_v2`.
- `fleet/discover.py` `Project` has `.name` and `.path` (the project dir that
  contains `ai/`) — the path to feed `read_gitstate`.
- `fleet/health.py` `classify_health_v2(days, last_outcome, git_state)` is the
  pure v2 classifier (Cycle 15) to reuse for the `stranded`/`paused` filter.

## Change
In `fleet/cli.py`:
- Extend `_VALID_FILTERS` to
  `("active", "stalled", "dead", "stranded", "paused", "all")`.
- Add `from fleet.gittest import EMPTY_STATE, read_gitstate` and
  `from fleet.health import classify_health_v2`.
- Add helper `_git_states(root: str) -> dict[str, GitState]` returning
  `{p.name: read_gitstate(p.path) for p in discover.discover(root)}`.
- In `_cmd_status`:
  - `healths = _assess_all(args.root)`; `git_states = _git_states(args.root)`.
  - if `args.filter != "all"`:
    - if `args.filter in ("stranded", "paused")`: keep rows where
      `classify_health_v2(h.days_since_activity, h.last_outcome,
      git_states.get(h.name, EMPTY_STATE)) == args.filter`.
    - else: keep rows where `h.health == args.filter` (unchanged v1 path).
  - `print(report.render_portfolio(healths, git_states))`; return 0.
- The `status` table now ALWAYS shows the Git column (pass `git_states`).
  For non-repo projects the Git cell is `-`.
- Do NOT change `_cmd_snapshot`, `_cmd_diff`, `_assess_all`, or `--version`.
