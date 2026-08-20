# fleet

A multi-project health scanner for the four pipeline.

`fleet` scans all project AI directories under a given root (default `~/AI`)
and emits a one-page portfolio status table. For each project it discovers
(any subdir containing an `ai/` with trajectories or a gate log), it uses the
`fourseer` parsers to extract: last cycle number, last outcome, days since
last activity, open issue count (from `gh` if available, else 0), and a health
classification.

## How it works

The portfolio table is produced by a four-stage pipeline:

1. **discover** (`fleet.discover.discover`) scans the root for project `ai/`
   directories at depth ≤ 2 that hold trajectories or a gate log.
2. **assess** (`fleet.health.assess` / `project_health`) extracts per-project
   metrics via the `fourseer` parsers: last cycle, last outcome, days since
   activity, and open issues.
3. **classify** (`fleet.health.classify_health`) maps those metrics to a v1
   health label: `active`, `stalled`, or `dead`. A second, git-aware scheme
   (`fleet.health.classify_health_v2`) classifies into four classes
   (`stranded` / `active` / `paused` / `dead`) — see below.
4. **render** (`fleet.report.render_portfolio`) emits the markdown table,
   sorted by last-activity descending (no-activity last).

## Health classification (v1)

`classify_health` is the recency-only scheme used by the `Health` column:

| Health     | Condition |
|------------|-----------|
| **active**   | has trajectories AND ≤ 7 days since activity |
| **stalled**  | has trajectories AND 8-30 days, OR has trajectories but no activity signal |
| **dead**     | no trajectories, OR > 30 days since activity |

## Health classification (v2)

`classify_health_v2(days, last_outcome, git_state)` is a pure, git-aware scheme
with **four classes**, resolved **most-severe-wins**
(`stranded` > `active` > `paused` > `dead`). "Work in flight" means an unmerged
`build*` branch, unpushed commits on `main`, or a last outcome of exactly
`max_steps_reached` (no other outcome counts as in-flight).

| Health       | Condition |
|--------------|-----------|
| **stranded** | an unmerged `build*` branch OR unpushed commits on `main`, regardless of recency (git work in flight) |
| **active**   | touched ≤ 7 days AND work in flight (last outcome `max_steps_reached`; an unmerged branch already → `stranded`) |
| **paused**   | recently touched but done (nothing in flight), or idle in the 8-29 day band with nothing in flight |
| **dead**     | 30+ days untouched AND nothing in flight, or no activity signal at all with nothing in flight |

> **v1/v2 30-day boundary divergence.** The two schemes intentionally disagree
> at exactly 30 days: v1 `dead` is `> 30` days (so 30 days is `stalled`), while
> v2 `dead` is `>= 30` days (so 30 days is `dead`). They are **not** unified —
> each is pinned by its own tests. Do not "normalize" one to match the other.

## CLI

    fleet status   [--root ~/AI] [--filter active|stalled|dead|stranded|paused|all]
    fleet snapshot [--root ~/AI] [--snapshot SNAPSHOT]
    fleet diff     [--root ~/AI] [--snapshot SNAPSHOT]

- `status` prints the current portfolio as a markdown table, optionally
  filtered by health (`active`/`stalled`/`dead`/`stranded`/`paused`/`all`).
  The v1 classes (`active`/`stalled`/`dead`) match the `Health` column; the two
  v2-only classes (`stranded`/`paused`) are selected with the v2 classifier
  over each project's git state. The table always shows a trailing `Git`
  column — a compact work-in-flight summary: `unmerged:<branch>` /
  `unpushed:<n>` / `-` when clean.
- `snapshot` saves the current portfolio as a snapshot JSON (the baseline that
  `diff` compares against). Each row now stores a `health_v2` field (the v2
  class computed from the project's git state).
- `diff` compares the current portfolio against a saved snapshot JSON and
  prints a markdown diff table. A v2 transition surfaces as a
  `health_v2 <a>-><b>` fragment (`-` for `None`). Old v1 snapshots (no
  `health_v2` key) still load, with `health_v2` defaulting to `None`.

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

## Example

The repo ships a small, self-contained example tree under `examples/` (the
directory itself is the scan root). Point `fleet` at it to see real output:

    fleet status --root examples/

The same drift loop works against it:

    fleet snapshot --root examples/ --snapshot baseline.json
    fleet diff     --root examples/ --snapshot baseline.json

> **Note:** health is mtime-based, so a freshly-checked-out tree shows recent
> activity (every example project reports `active` right after a clone).

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
