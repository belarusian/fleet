# TICKET-077: Release verification — gate green, --version prints 0.2.0, tag decision

## Title
Cut the 0.2.0 release: confirm the full gate is green, confirm `--version`
prints `fleet 0.2.0`, and record the decision on whether to create a `v0.2.0`
git tag.

## Evidence
- `fleet/cli.py` — the top-level `--version` flag already exists
  (`action="version"`, `version=f"fleet {__version__}"`); after the bump it
  prints `fleet 0.2.0`. No new flag is needed.
- `git tag -l` — returns empty: the repo has **no prior tags**. Per the
  Cycle 19 briefing, a tag is optional when there are no prior tags and may be
  skipped to keep the cycle minimal.

## Change / Decision
- Verify the gate: `pytest tests/ -x -q`, `ruff check fleet/`,
  `mypy fleet/ --ignore-missing-imports` — all green.
- Verify `python3 -m fleet --version` prints exactly `fleet 0.2.0` and exits 0.
- **Tag decision: skip the `v0.2.0` tag.** The repo has no prior tags, so a
  single tag would not establish a tagging convention and the briefing marks
  it optional. Revisit tagging when a convention is adopted.

## Acceptance
- All pre-existing tests (report/cli/integration/integration_v2/snapshot/
  health/gittest/smoke/examples) stay green.
- `fleet --version` prints `fleet 0.2.0`.
- No `fleet/` source logic changed (only the `__version__` string in
  `fleet/__init__.py`); the release is docs + version only.
