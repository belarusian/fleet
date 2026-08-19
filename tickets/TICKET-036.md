# TICKET-036 — Decision: defer project→repo mapping to the Polish phase

**Phase:** Cycle 8 synthesis audit
**Status:** DECISION (deferred)

## Problem
The Cycle 7 open-issue decision documented that the CLI reports `open_issues=0`
by design because the discovery layer has no project → `owner/repo` mapping.
The Cycle 8 briefing asks whether to introduce a lightweight mapping (a
per-project `fleet.toml` or a `--repo` flag) so the CLI can pass a repo to
`assess` and get real `gh`-backed counts.

## Decision
**Defer to the Polish + Release phase (cycles 10-12).**

Rationale:
- A repo mapping is a *new feature* (a config convention or a new CLI flag),
  not robustness or polish. This cycle is the *phase close* for
  Open-issue + Robustness, whose remaining concrete work is the robustness
  edges and the mixed-root integration (TICKET-033/034/035).
- The `open_issues=0` CLI behavior is already documented (cli.py + README) and
  pinned by `test_cli_open_issues_always_zero` (Cycle 7), so deferring leaves
  the current behavior correct and tested.
- If implemented later, the CLI expected-table helpers must then pass the
  mapped repo (Cycle 4/5 lesson) so the open-issue column stays consistent.

## Impact
No code change this cycle. The CLI continues to report `open_issues=0`;
programmatic callers can already pass `repo` to `assess`/`project_health`.

## Follow-up
Record in the Cycle 8 log and the Cycle 9 / Polish-phase briefing as a
candidate feature for the bounded POLISH class.
