# TICKET-028 — count_open_issues is always 0 in CLI output (by-design, undocumented)

**Phase:** Cycle 7 synthesis audit
**Status:** OPEN

## Problem
`fleet.cli._assess_all` (cli.py:68) calls `health_mod.assess(p.name, p.ai_dir)`
without a `repo` argument. The `assess` function defaults `repo=None`, which
causes `count_open_issues(None)` to return 0 (health.py:139). Therefore the
`open_issues` column in every CLI-rendered portfolio table is always 0.

## Evidence
- `cli.py:68`: `return [health_mod.assess(p.name, p.ai_dir) for p in projects]`
- `health.py:139`: `if not repo: return 0`
- `health.py:189`: `open_issues = count_open_issues(repo)` (repo defaults to None)
- No `--repo` flag exists on any CLI subcommand.
- The test `test_cli_status_matches_render_portfolio` (test_cli.py) explicitly
  notes: "The CLI's `_assess_all` calls `assess(name, ai_dir)` with no `repo`,
  so `count_open_issues(None)` returns 0 for every row."

## Impact
- The `open_issues` column in `fleet status` output is always 0, which is
  misleading to a reader who expects it to reflect real GitHub issue counts.
- A future developer may assume the CLI is broken when it isn't.

## Decision
**By-design.** The discovery layer (`fleet.discover`) has no concept of a
GitHub repo mapping (project name → owner/repo). Adding one would require a
config file or convention (e.g., a `.fleet.toml` per project). Until such a
mapping exists, `open_issues` is 0 in CLI output. The `assess` and
`project_health` APIs still accept a `repo` parameter for programmatic use.

## Suggestion
1. Add a docstring note to `cli.py`'s `_assess_all` documenting that
   `open_issues` is always 0 in CLI mode (no repo mapping).
2. Add a test `test_cli_open_issues_always_zero` that asserts every row in
   `fleet status` output has `open_issues == 0` even when `count_open_issues`
   would return a non-zero value if a repo were passed.
3. Update `README.md` to note that `open_issues` is 0 in CLI output.

## Tests
- New: `test_cli_open_issues_always_zero` in `tests/test_cli.py`.
