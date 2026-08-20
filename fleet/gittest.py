"""Git-side "work in flight" signal for a project repo.

For a project repository, :func:`read_gitstate` inspects the local git state
to report the two signals that ``classify_health`` v2 (stranded / active /
paused / dead) will consume in a later cycle:

  - ``unmerged_build_branches`` — local branches whose names start with
    ``build`` that have at least one commit not reachable from ``main``.
  - ``unpushed_commits`` — commits on ``main`` not reachable from
    ``origin/main`` (or ``main``'s upstream when there is no ``origin``).

All git access is via ``git -C {repo} ...`` and never raises: a missing
path, a non-repo directory, a repo without a ``main`` branch, or any git
failure yields the empty state :data:`EMPTY_STATE`.
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path

# Timeout (seconds) for every git subprocess call.
_GIT_TIMEOUT = 30


@dataclass(frozen=True)
class GitState:
    """Git-side work-in-flight signal for one project repo.

    Attributes
    ----------
    unmerged_build_branches:
        Sorted local branch names starting with ``build`` that have >= 1
        commit not reachable from ``main``.
    unpushed_commits:
        Commits on ``main`` not reachable from ``origin/main`` (or its
        upstream). ``0`` when there is no upstream.
    """

    unmerged_build_branches: tuple[str, ...]
    unpushed_commits: int


# The empty / "no signal" state returned on any failure.
EMPTY_STATE = GitState((), 0)


def _git(repo: Path, *args: str) -> str | None:
    """Run ``git -C {repo} {args}`` and return stdout, or ``None`` on failure.

    Any error (missing binary, non-zero exit, timeout) yields ``None`` so the
    caller can treat it as "no signal" rather than propagating an exception.
    """
    try:
        proc = subprocess.run(
            ["git", "-C", str(repo), *args],
            capture_output=True,
            text=True,
            timeout=_GIT_TIMEOUT,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if proc.returncode != 0:
        return None
    return proc.stdout


def _count(a: str | None) -> int:
    """Parse a ``rev-list --count`` stdout value into a non-negative int."""
    if a is None:
        return 0
    s = a.strip()
    return int(s) if s else 0


def _local_branches(repo: Path) -> list[str]:
    """Return the short names of all local branches (empty on failure)."""
    out = _git(repo, "for-each-ref", "--format=%(refname:short)", "refs/heads/")
    if out is None:
        return []
    return [ln.strip() for ln in out.splitlines() if ln.strip()]


def _unmerged_build_branches(repo: Path) -> tuple[str, ...]:
    """Sorted local ``build*`` branches with >= 1 commit not on ``main``."""
    candidates = [b for b in _local_branches(repo) if b.startswith("build")]
    unmerged = [
        b
        for b in candidates
        if _count(_git(repo, "rev-list", "--count", f"main..{b}")) > 0
    ]
    return tuple(sorted(unmerged))


def _unpushed_commits(repo: Path) -> int:
    """Commits on ``main`` not on ``origin/main`` (or its upstream), else 0."""
    out = _git(repo, "rev-list", "--count", "origin/main..main")
    if out is not None:
        return _count(out)
    out = _git(repo, "rev-list", "--count", "@{u}..main")
    if out is not None:
        return _count(out)
    return 0


def read_gitstate(repo_path: str | Path) -> GitState:
    """Read the git work-in-flight signal for *repo_path*.

    Never raises: a missing path, a non-repo directory, a repo without a
    ``main`` branch, or any git failure yields :data:`EMPTY_STATE`.
    """
    repo = Path(repo_path).expanduser()
    if not repo.is_dir():
        return EMPTY_STATE
    if _git(repo, "rev-parse", "--is-inside-work-tree") is None:
        return EMPTY_STATE
    if _git(repo, "rev-parse", "--verify", "--quiet", "refs/heads/main") is None:
        return EMPTY_STATE
    return GitState(
        unmerged_build_branches=_unmerged_build_branches(repo),
        unpushed_commits=_unpushed_commits(repo),
    )
