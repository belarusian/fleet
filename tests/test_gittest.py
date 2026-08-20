"""Tests for fleet.gittest (git-side work-in-flight signal).

All fixtures are hermetic: real git repos built in ``tmp_path`` via
``git init`` (with a ``git init -b main`` / ``git checkout -b main``
fallback) and a ``git init --bare`` fake origin. Nothing touches ``~/AI``
or the ambient CWD.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

from fleet import gittest
from fleet.gittest import GitState


def _git(repo: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True,
        text=True,
        check=False,
    )


def _init_repo(repo: Path) -> None:
    """Create a git repo with a ``main`` branch and a local identity."""
    repo.mkdir(parents=True, exist_ok=True)
    r = _git(repo, "init", "-b", "main")
    if r.returncode != 0:
        _git(repo, "init")
        _git(repo, "checkout", "-b", "main")
    _git(repo, "config", "user.name", "Test")
    _git(repo, "config", "user.email", "test@example.com")


def _commit(repo: Path, name: str, content: str) -> None:
    (repo / name).write_text(content)
    _git(repo, "add", "-A")
    _git(repo, "commit", "-m", name)


def test_missing_path_returns_empty(tmp_path: Path) -> None:
    """A missing path yields the empty state without raising."""
    assert gittest.read_gitstate(tmp_path / "does-not-exist") == GitState((), 0)


def test_non_repo_dir_returns_empty(tmp_path: Path) -> None:
    """A plain non-repo directory yields the empty state without raising."""
    d = tmp_path / "plain"
    d.mkdir()
    assert gittest.read_gitstate(d) == GitState((), 0)


def test_repo_without_main_returns_empty(tmp_path: Path) -> None:
    """A repo whose only branch is not ``main`` yields the empty state."""
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-b", "develop")
    _git(repo, "config", "user.name", "Test")
    _git(repo, "config", "user.email", "test@example.com")
    _commit(repo, "a.txt", "a")
    assert gittest.read_gitstate(repo) == GitState((), 0)


def test_fully_merged_build_branch_not_reported(tmp_path: Path) -> None:
    """A ``build*`` branch fully merged into ``main`` is not reported."""
    repo = tmp_path / "repo"
    _init_repo(repo)
    _commit(repo, "a.txt", "a")
    _git(repo, "checkout", "-b", "build1/done")
    _commit(repo, "b.txt", "b")
    _git(repo, "checkout", "main")
    _git(repo, "merge", "--no-ff", "build1/done")
    assert gittest.read_gitstate(repo) == GitState((), 0)


def test_unmerged_build_branch_reported(tmp_path: Path) -> None:
    """A ``build*`` branch 2 commits ahead of ``main`` is reported unmerged."""
    repo = tmp_path / "repo"
    _init_repo(repo)
    _commit(repo, "a.txt", "a")
    _git(repo, "checkout", "-b", "build9/unmerged")
    _commit(repo, "b.txt", "b")
    _commit(repo, "c.txt", "c")
    state = gittest.read_gitstate(repo)
    assert state.unmerged_build_branches == ("build9/unmerged",)
    assert state.unpushed_commits == 0


def test_unpushed_commits_against_bare_origin(tmp_path: Path) -> None:
    """``main`` 3 commits ahead of a bare-origin ``origin/main`` -> 3 unpushed."""
    origin = tmp_path / "origin.git"
    origin.mkdir()
    _git(origin, "init", "--bare", "-b", "main")
    repo = tmp_path / "repo"
    _init_repo(repo)
    _commit(repo, "a.txt", "a")
    _git(repo, "remote", "add", "origin", str(origin))
    _git(repo, "push", "origin", "main")
    _commit(repo, "b.txt", "b")
    _commit(repo, "c.txt", "c")
    _commit(repo, "d.txt", "d")
    state = gittest.read_gitstate(repo)
    assert state.unpushed_commits == 3
    assert state.unmerged_build_branches == ()


def test_two_unmerged_build_branches_sorted(tmp_path: Path) -> None:
    """Two unmerged ``build*`` branches are reported as a sorted tuple."""
    repo = tmp_path / "repo"
    _init_repo(repo)
    _commit(repo, "a.txt", "a")
    _git(repo, "checkout", "-b", "build2/second")
    _commit(repo, "b.txt", "b")
    _git(repo, "checkout", "main")
    _git(repo, "checkout", "-b", "build1/first")
    _commit(repo, "c.txt", "c")
    _git(repo, "checkout", "main")
    state = gittest.read_gitstate(repo)
    assert state.unmerged_build_branches == ("build1/first", "build2/second")
    assert state.unpushed_commits == 0
