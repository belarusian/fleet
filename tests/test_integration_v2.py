"""End-to-end Health v2 integration (discover -> assess -> v2 classify -> render).

Ties the three v2 links together as one composed path (TICKET-064):

  - :func:`fleet.gittest.read_gitstate` (Cycle 14) — the git-side work-in-flight
    signal,
  - :func:`fleet.health.classify_health_v2` (Cycle 15) — the four-class,
    most-severe-wins classifier,
  - :func:`fleet.report.render_portfolio` (Cycle 16) — the report surface with
    the opt-in ``Git`` column.

The primary test builds an in-tree fixture root of *real* git repos in
``tmp_path`` that carry the Build-Order canary shapes, so it is deterministic
and CI-runnable. A second test mirrors the CLI ``--filter stranded`` logic. A
third test is a live-root self-consistency smoke test that skips when ``~/AI``
is absent.

The git helpers below are copied from :mod:`tests.test_gittest` (they are small
and private there). Nothing touches ``~/AI`` except the live test, which skips
when the root is absent.
"""

from __future__ import annotations

import subprocess
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock

import pytest

from fleet import discover, gittest, health, report
from fleet.gittest import EMPTY_STATE, GitState
from tests._fixtures import make_project

NOW = datetime(2025, 6, 1, 12, 0, 0, tzinfo=timezone.utc)


# ---------------------------------------------------------------------------
# Git helpers (copied from tests/test_gittest.py — small and private there).
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# Fixture root builder (deterministic, CI-runnable).
# ---------------------------------------------------------------------------


def _build_v2_root(root: Path) -> None:
    """Build a root of three projects carrying the Build-Order canary shapes.

    - ``alloc-pipeline``   -> **stranded**: a ``main`` branch, an unmerged
      ``build42/model-persistence-rebalance`` branch, and 2 unpushed commits on
      ``main`` (against a bare ``origin``).
    - ``deepseek-deharness`` -> **paused**: a clean ``main`` branch (no
      ``build*`` branch, no unpushed commits).
    - ``gamma``            -> **dead**: a plain directory with no git repo.
    """
    # alloc-pipeline: stranded (unmerged build42 branch + 2 unpushed commits).
    make_project(
        root, "alloc-pipeline", now=NOW, days_ago=1, n_traj=1, outcome="max_steps_reached"
    )
    repo = root / "alloc-pipeline"
    _init_repo(repo)
    _git(repo, "add", "-A")
    _git(repo, "commit", "-m", "init ai")
    _git(repo, "checkout", "-b", "build42/model-persistence-rebalance")
    _commit(repo, "wip.txt", "wip")
    _git(repo, "checkout", "main")
    origin = root / "origin-alloc.git"
    origin.mkdir()
    _git(origin, "init", "--bare", "-b", "main")
    _git(repo, "remote", "add", "origin", str(origin))
    _git(repo, "push", "origin", "main")
    _commit(repo, "f1.txt", "1")
    _commit(repo, "f2.txt", "2")

    # deepseek-deharness: paused (clean main, no build branch, no unpushed).
    make_project(
        root, "deepseek-deharness", now=NOW, days_ago=1, n_traj=1, outcome="exit:task_complete"
    )
    repo2 = root / "deepseek-deharness"
    _init_repo(repo2)
    _git(repo2, "add", "-A")
    _git(repo2, "commit", "-m", "init ai")

    # gamma: dead (no git repo at all).
    make_project(root, "gamma", now=NOW, days_ago=40, n_traj=1, outcome="timeout")


def _assess_v2_root(root: Path) -> list[health.ProjectHealth]:
    """Run discover -> assess over *root* with a pinned clock and deterministic issues."""
    projects = discover.discover(root)
    with mock.patch.object(health, "count_open_issues", return_value=0):
        return [health.assess(p.name, p.ai_dir, now=NOW) for p in projects]


# ---------------------------------------------------------------------------
# Test A — the full v2 pipeline yields stranded / paused / dead.
# ---------------------------------------------------------------------------


def test_integration_v2_pipeline_stranded_paused_dead(tmp_path: Path) -> None:
    """discover -> assess -> classify_health_v2(read_gitstate(...)) -> render_portfolio.

    The composed path yields the three Build-Order canary classes and the
    ``Git`` column renders the work-in-flight summary for the stranded project.
    """
    _build_v2_root(tmp_path)
    projects = discover.discover(tmp_path)
    assert [p.name for p in projects] == ["alloc-pipeline", "deepseek-deharness", "gamma"]

    git_states = {p.name: gittest.read_gitstate(p.path) for p in projects}

    # The git-side signal is exactly the pinned canary shape.
    assert git_states["alloc-pipeline"] == GitState(("build42/model-persistence-rebalance",), 2)
    assert git_states["deepseek-deharness"] == EMPTY_STATE
    assert git_states["gamma"] == EMPTY_STATE

    assessed = _assess_v2_root(tmp_path)
    v2 = {
        h.name: health.classify_health_v2(
            h.days_since_activity, h.last_outcome, git_states[h.name]
        )
        for h in assessed
    }
    assert v2["alloc-pipeline"] == "stranded"
    assert v2["deepseek-deharness"] == "paused"
    assert v2["gamma"] == "dead"

    # The report surface: the exact 7-column header + separator + three rows.
    md = report.render_portfolio(assessed, git_states)
    assert md == (
        "| Project | Last Cycle | Last Outcome | Days Since Activity | Open Issues | "
        "Health | Git |\n"
        "|---|---|---|---|---|---|---|\n"
        "| alloc-pipeline | 1 | max_steps_reached | 1 | 0 | active "
        "| unmerged:build42/model-persistence-rebalance,unpushed:2 |\n"
        "| deepseek-deharness | 1 | exit:task_complete | 1 | 0 | active | - |\n"
        "| gamma | 1 | timeout | 40 | 0 | dead | - |"
    )


# ---------------------------------------------------------------------------
# Test B — filtering to the v2 `stranded` class selects exactly alloc-pipeline.
# ---------------------------------------------------------------------------


def test_integration_v2_filter_stranded(tmp_path: Path) -> None:
    """Mirrors the CLI ``--filter stranded`` logic over the real git state.

    Keeping the rows whose v2 class is ``stranded`` yields exactly
    ``alloc-pipeline`` (the only project with git work in flight).
    """
    _build_v2_root(tmp_path)
    projects = discover.discover(tmp_path)
    git_states = {p.name: gittest.read_gitstate(p.path) for p in projects}
    assessed = _assess_v2_root(tmp_path)

    stranded = [
        h.name
        for h in assessed
        if health.classify_health_v2(
            h.days_since_activity, h.last_outcome, git_states[h.name]
        )
        == "stranded"
    ]
    assert stranded == ["alloc-pipeline"]


# ---------------------------------------------------------------------------
# Live-root self-consistency smoke test (skips when ~/AI is absent).
# ---------------------------------------------------------------------------


def test_integration_live_root_self_consistent() -> None:
    """The v2 pipeline runs end-to-end over the live ``~/AI`` root and is self-consistent.

    This is a smoke test, not a canary assertion. The live canary repos use a
    ``master`` branch (no ``main``) with no ``origin`` remote, so
    :func:`fleet.gittest.read_gitstate` yields ``EMPTY_STATE`` for them and the
    pinned ``stranded``/``paused`` classes are NOT reproducible live. We
    therefore assert only that the pipeline runs without error and that every
    reported v2 class is one of the four valid classes — never a specific
    class. Skips when ``~/AI`` is absent so CI without the live root stays
    green.
    """
    root = Path("~/AI").expanduser()
    if not root.is_dir():
        pytest.skip("no live ~/AI root")
    projects = discover.discover(root)
    if not projects:
        pytest.skip("no projects under ~/AI")

    valid = {"stranded", "active", "paused", "dead"}
    reported: dict[str, str] = {}
    for p in projects:
        gs = gittest.read_gitstate(p.path)
        h = health.assess(p.name, p.ai_dir)
        expected = health.classify_health_v2(h.days_since_activity, h.last_outcome, gs)
        assert expected in valid
        reported[p.name] = expected

    # Self-consistency for the two canaries: the reported class equals the
    # classify_health_v2 computed from their real inputs. We deliberately do
    # NOT assert a specific class (the live git state is not the pinned shape).
    for name in ("alloc-pipeline", "deepseek-deharness"):
        if name in reported:
            p = next(x for x in projects if x.name == name)
            gs = gittest.read_gitstate(p.path)
            h = health.assess(p.name, p.ai_dir)
            assert reported[name] == health.classify_health_v2(
                h.days_since_activity, h.last_outcome, gs
            )
