# fleet

A multi-project health scanner for the four pipeline.

`fleet` scans all project AI directories under a given root (default `~/AI`)
and emits a one-page portfolio status table. For each project it discovers
(any subdir containing an `ai/` with trajectories or a gate log), it uses the
`fourseer` parsers to extract: last cycle number, last outcome, days since
last activity, open issue count (from `gh` if available, else 0), and a health
classification:

- **active** — ran within 7 days
- **stalled** — 8-30 days
- **dead** — more than 30 days or no trajectories

## CLI

    fleet status   [--root ~/AI] [--filter active|stalled|dead|all]
    fleet snapshot [--root ~/AI] [--snapshot SNAPSHOT]
    fleet diff     [--root ~/AI] [--snapshot SNAPSHOT]

- `status` prints the current portfolio as a markdown table, optionally
  filtered by health (`active`/`stalled`/`dead`/`all`).
- `snapshot` saves the current portfolio as a snapshot JSON (the baseline that
  `diff` compares against).
- `diff` compares the current portfolio against a saved snapshot JSON and
  prints a markdown diff table.

Output is a markdown table sorted by last-activity descending.

## Workflow

The three subcommands compose into a drift-detection loop:

    fleet status                            # 1. view the current portfolio
    fleet snapshot --snapshot baseline.json # 2. save a baseline
    fleet diff --snapshot baseline.json     # 3. see what changed since

1. `status` shows the current health of every project under the root.
2. `snapshot` saves that portfolio as a JSON baseline.
3. `diff` compares the next run against the baseline and reports what was
   added, removed, or changed.

> **Note:** the `open_issues` column is always `0` in CLI output. The CLI has
> no project -> `owner/repo` mapping, so it never resolves a repo for the `gh`
> lookup. Programmatic callers can pass `repo` to `fleet.health.assess` /
> `fleet.health.project_health` to get real `gh`-backed counts.

Stdlib-first; the only dependency is the `fourseer` package.

## Development

    pip install -e .
    pytest tests/ -x -q
    ruff check fleet/
    mypy fleet/ --ignore-missing-imports
