# TICKET-057: fleet/__init__.py — export `gittest` in the public surface

## Title
Add `gittest` to the `__all__` list and the public-surface docstring in
`fleet/__init__.py`, so `fleet.gittest` (and its `GitState` / `read_gitstate`)
is part of the documented public API.

## Evidence
- `fleet/__init__.py` `__all__` currently lists: `__version__`, `discover`,
  `health`, `report`, `snapshot`, `cli`. It does NOT list `gittest`
  (grep for `gittest` in `__init__.py` returns nothing).
- The module docstring's "Public surface" block lists discover / health /
  report / snapshot / cli — again no `gittest`.
- `fleet/gittest.py` is a real, merged module (Cycle 14, commit 6b13cc4)
  exposing `read_gitstate` and `GitState`. It is importable as
  `fleet.gittest` (the package is a plain `packages = ["fleet"]`), but it is
  absent from the documented public surface.
- `fleet/health.py` will import `GitState` from `fleet.gittest` (TICKET-055),
  making `gittest` a load-bearing public dependency of the health module.

## Impact
A newcomer reading `fleet/__init__.py` (or `dir(fleet)`) sees no `gittest`,
so the git-state input that the v2 health classifier consumes is invisible in
the public surface. This is a documentation/consistency gap, not a runtime
break — `import fleet.gittest` works today.

## Suggestion
- Add `"gittest"` to `__all__` (keep it sorted / grouped with the other
  submodules).
- Add a line to the "Public surface" docstring, e.g.:
  `  - fleet.gittest  : git-side work-in-flight signal (GitState, read_gitstate)`.
- Do NOT change the seed-bootstrap `sys.path` logic or `__version__`.
- Gate: `pytest tests/ -x -q`, `ruff check fleet/`,
  `mypy fleet/ --ignore-missing-imports`.
