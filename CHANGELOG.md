# Changelog

All notable changes to `fleet` are documented here. The format is loosely
based on [Keep a Changelog](https://keepachangelog.com/), and the project
adheres to [Semantic Versioning](https://semver.org/).

## [0.2.0] - 2026-08-20

Second release: **Health v2**. Adds a git-aware, four-class health scheme
(`stranded` / `active` / `paused` / `dead`) that runs alongside the v1
recency-only scheme, and ships it end-to-end through the report, CLI, and
snapshot layers. The v2 classifier is a pure function of days-since-activity,
last outcome, and a git-side work-in-flight signal; it resolves
**most-severe-wins** (`stranded` > `active` > `paused` > `dead`), and only the
exact outcome `max_steps_reached` counts as "work in flight". The v1 and v2
dead boundaries intentionally diverge at exactly 30 days (v1 `> 30`, v2
`>= 30`) and are not unified.

### Added

- **Git-side signal** (`fleet.gittest`): `read_gitstate(repo_path) ->
  GitState(unmerged_build_branches, unpushed_commits)` and `EMPTY_STATE`.
  Reports local `build*` branches with commits not on `main` and unpushed
  commits on `main`; never raises (missing repo / no `origin` / no `main` /
  any git failure → `EMPTY_STATE`).
- **v2 classifier** (`fleet.health.classify_health_v2`): a pure, four-class,
  most-severe-wins classifier (`stranded` / `active` / `paused` / `dead`).
  `stranded` = an unmerged `build*` branch OR unpushed commits on `main`,
  regardless of recency; `active` = touched ≤ 7 days AND work in flight;
  `paused` = recently touched but done, or idle in the 8-29 day band; `dead`
  = 30+ days untouched (or no activity signal) with nothing in flight.
- **`ProjectHealth.health_v2`**: a defaulted field (`None`) carrying the v2
  class when known.
- **Report** (`fleet.report`): `render_portfolio(..., git_states=...)` gains an
  opt-in trailing `Git` column (a compact work-in-flight summary:
  `unmerged:<branch>` / `unpushed:<n>` / `-` when clean).
- **CLI** (`fleet.cli`): `status` always shows the `Git` column; `--filter`
  now accepts `stranded` / `paused` (selected with the v2 classifier over each
  project's git state) in addition to the v1 `active` / `stalled` / `dead` /
  `all`.
- **Snapshot v2** (`fleet.snapshot`): `save_snapshot(..., git_states=...)`
  computes and stores a per-row `health_v2`; `snapshot_diff` surfaces a
  `health_v2 <a>-><b>` fragment (`-` for `None`); old v1 snapshots (no
  `health_v2` key) still load with `health_v2` defaulting to `None`.
- **Integration**: an end-to-end v2 pipeline test (in-tree fixture) plus a
  live-root self-consistency smoke test.

### Notes

- The v1 `Health` column and `classify_health` are unchanged; v2 is additive.
- The v1/v2 30-day dead-boundary divergence (`> 30` vs `>= 30`) is intentional
  and pinned by tests in both schemes.

## [0.1.0] - 2026-08-19

First release. `fleet` is a multi-project health scanner for the four
pipeline: it scans all project `ai/` directories under a root (default
`~/AI`) and emits a one-page portfolio status table, with snapshot/diff
drift detection. Stdlib-first; the only dependency is the `fourseer`
package (imported from the seed).

### Added

- **Discovery** (`fleet.discover`): `discover(root)` finds every project
  `ai/` directory at depth ≤ 2 that holds trajectories or a gate log;
  `is_project` is the single predicate; `Project` / `ProjectRef` dataclass.
- **Health metrics** (`fleet.health`): `assess` / `project_health` extract
  last cycle, last outcome, days since activity, and open-issue count via the
  `fourseer` parsers; `count_open_issues` is best-effort `gh` (returns `0` on
  any failure or when no repo is given).
- **Classification** (`fleet.health.classify_health`): maps metrics to
  `active` (≤ 7 days), `stalled` (8-30 days, or trajectories with no activity
  signal), or `dead` (no trajectories, or > 30 days).
- **Report** (`fleet.report.render_portfolio`): a markdown portfolio table
  sorted by last-activity descending (no-activity last).
- **Snapshot** (`fleet.snapshot`): `save_snapshot` / `load_snapshot`
  (JSON round-trip) and `snapshot_diff` / `render_diff` for drift detection.
- **CLI** (`fleet.cli`, entrypoint `fleet`):
  - `fleet status [--root DIR] [--filter active|stalled|dead|all]`
  - `fleet snapshot [--root DIR] [--snapshot FILE]`
  - `fleet diff [--root DIR] [--snapshot FILE]`
  - `--root` defaults to `~/AI` on every subcommand; `diff` is unfiltered by
    design; `diff` exits `2` when the snapshot is missing.
  - `fleet --version` prints `fleet <__version__>` and exits `0` (top-level
    flag, not a subcommand).
- **Robustness**: edge-case coverage for empty/unparseable gate logs,
  wall-clock-killed cycles, `ai/` as a file, missing `outcome` keys,
  malformed `cycles.out` headers, non-string outcomes, and mixed-root
  pipelines.
- **Docs**: README with a "How it works" pipeline section, a
  health-threshold table, and a workflow example.
- **Examples**: a self-contained `examples/` tree (scan root) referenced by
  the README and pinned by `tests/test_examples.py`.
- **Release**: `CHANGELOG.md`, a top-level `--version` flag, and version
  tests pinning `fleet.__version__ == "0.1.0"`.

### Notes

- The `open_issues` column is always `0` in CLI output: the CLI has no
  project → `owner/repo` mapping, so it never resolves a repo for the `gh`
  lookup. Programmatic callers can pass `repo` to `fleet.health.assess` /
  `fleet.health.project_health` for real `gh`-backed counts.
- A `--json` flag was considered and declined (no consumer needs it).
