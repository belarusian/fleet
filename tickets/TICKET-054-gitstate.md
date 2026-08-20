# TICKET-054: fleet/gittest.py — read_gitstate(repo_path) -> GitState

## Title
Add `fleet/gittest.py` exposing `read_gitstate(repo_path) -> GitState`: the
git-side "work in flight" signal for a project repo (unmerged `build*`
branches, unpushed commits on `main`). This is the cycle-15 input for
`classify_health` v2 (stranded / active / paused / dead — see Build Order,
gate log).

## Evidence
- fleet v0.2 (Build Order cycles 14-19): health must distinguish
  *stranded* (unmerged `build*` branch OR unpushed commits on main,
  regardless of recency) from *active* / *paused* / *dead*. Today
  `fleet/health.py` has only the days-since-activity signal
  (`classify_health` thresholds 7/30); there is no git-state input.
- Real examples to match once wired: `~/AI/alloc-pipeline/proj` has local
  branch `build42/model-persistence-rebalance` with 3 commits ahead of
  `main` (unmerged) -> must yield a non-empty
  `unmerged_build_branches`; a project whose local `main` leads
  `origin/main` -> must yield `unpushed_commits > 0`.

## Change
- `fleet/gittest.py` (new module, stdlib only):
  - `@dataclass(frozen=True) GitState`:
    - `unmerged_build_branches: tuple[str, ...]` — sorted local branch
      names starting with `build` that have >= 1 commit not reachable
      from `main`
    - `unpushed_commits: int` — commits on `main` not reachable from
      `origin/main` (or its upstream, see below)
  - `read_gitstate(repo_path: str | Path) -> GitState`:
    - All git access via
      `subprocess.run(["git", "-C", str(repo_path), ...], capture_output=True, text=True, timeout=30)`.
      NEVER raises: return the empty state `GitState((), 0)` when the
      path is missing, is not a git repo, has no `main` branch, or any
      git command fails.
    - Git commands (behavior is pinned by the acceptance section; the
      exact forms are suggestions):
      - local branches: `git -C {repo} for-each-ref --format="%(refname:short)" refs/heads/`
        -> keep names starting with `build`
      - unmerged: per candidate `git -C {repo} rev-list --count "main..{branch}"`
        (> 0 => unmerged)
      - unpushed: `git -C {repo} rev-list --count "origin/main..main"`;
        if there is no `origin` remote but `main` has an upstream, fall
        back to `git -C {repo} rev-list --count "@{u}..main"`; if neither,
        `unpushed_commits = 0`.
    - No CWD or `~/AI` dependency (must pass on a fresh CI clone).
- `tests/test_gittest.py` (new), hermetic fixtures built with `git init`
  in `tmp_path` (set local `user.name` / `user.email`; use
  `git init -b main` with a `git checkout -b main` fallback, and a
  `git init --bare` for the fake origin):
  1. missing path -> `GitState((), 0)`, no exception
  2. plain non-repo directory -> `GitState((), 0)`
  3. repo with `main` + fully-merged `build1/done` -> `GitState((), 0)`
  4. `build9/unmerged` 2 commits ahead of `main` ->
     `unmerged_build_branches == ("build9/unmerged",)`, `unpushed_commits == 0`
  5. `main` 3 commits ahead of bare-origin `origin/main` ->
     `unpushed_commits == 3`
  6. two unmerged build branches -> sorted tuple, stable order

## Acceptance
- `read_gitstate` never raises: missing path, non-repo dir, repo without
  `main`, and repo without `origin` all -> `GitState((), 0)` (the last
  with a real `main` simply reports 0 unpushed).
- Merged `build*` branches are NOT reported (only unmerged ones).
- Gate green: `pytest tests/ -x -q`, `ruff check fleet/`,
  `mypy fleet/ --ignore-missing-imports`.
