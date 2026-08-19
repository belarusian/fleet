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
- **dead** — 30+ days or no trajectories

## CLI

    fleet status [--root ~/AI] [--filter active|stalled|dead|all]
    fleet diff   # compare against a saved snapshot JSON

Output is a markdown table sorted by last-activity descending.

Stdlib-first; the only dependency is the `fourseer` package.

## Development

    pip install -e .
    pytest tests/ -x -q
    ruff check fleet/
    mypy fleet/ --ignore-missing-imports
