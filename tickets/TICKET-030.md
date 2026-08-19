# TICKET-030 — Document that open_issues is 0 in CLI output (README)

**Phase:** Cycle 7 (Open-issue + Robustness)
**Status:** OPEN

## Problem
`fleet status` always renders `open_issues` as 0 because the CLI never passes a
`repo` to `assess` (see TICKET-028). The README currently says "open issue count
(from `gh` if available, else 0)" without noting that the *CLI* path is always 0.

## Decision
By-design: the discovery layer has no project->`owner/repo` mapping, so the CLI
cannot resolve a repo. The `assess`/`project_health` APIs still accept `repo`
for programmatic use.

## Suggestion
- Add a one-line note to `README.md` (CLI section) that `open_issues` is 0 in
  CLI output until a repo mapping exists, and that `assess(..., repo=...)`
  yields real counts for programmatic callers.

## Tests
- No new test required (behavior is pinned by TICKET-028's
  `test_cli_open_issues_always_zero`).
