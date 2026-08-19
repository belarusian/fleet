# Changelog

All notable changes to `fleet` are documented here. The format is loosely
based on [Keep a Changelog](https://keepachangelog.com/), and the project
adheres to [Semantic Versioning](https://semver.org/).

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
