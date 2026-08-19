"""Tests for fleet.discover."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from fleet import discover
from tests._fixtures import make_project

NOW = datetime(2025, 6, 1, 12, 0, 0, tzinfo=timezone.utc)


def test_discover_finds_projects(tmp_path: Path) -> None:
    """Projects with an ai/ holding trajectories are discovered."""
    make_project(tmp_path, "alpha", now=NOW, days_ago=1)
    make_project(tmp_path, "beta", now=NOW, days_ago=2)

    found = discover.discover(tmp_path)
    names = [p.name for p in found]
    assert names == ["alpha", "beta"]
    assert found[0].ai_dir == tmp_path / "alpha" / "ai"


def test_discover_sorted_by_name(tmp_path: Path) -> None:
    """Discovery returns projects sorted by name regardless of creation order."""
    make_project(tmp_path, "zeta", now=NOW, days_ago=1)
    make_project(tmp_path, "alpha", now=NOW, days_ago=1)
    make_project(tmp_path, "mid", now=NOW, days_ago=1)

    names = [p.name for p in discover.discover(tmp_path)]
    assert names == ["alpha", "mid", "zeta"]


def test_discover_ignores_non_projects(tmp_path: Path) -> None:
    """Directories without an ai/ (or an empty ai/) are not projects."""
    (tmp_path / "empty").mkdir()
    (tmp_path / "noai").mkdir()
    (tmp_path / "noai" / "ai").mkdir()  # ai/ but no trajectories or gate log
    make_project(tmp_path, "real", now=NOW, days_ago=1)

    names = [p.name for p in discover.discover(tmp_path)]
    assert names == ["real"]


def test_discover_gate_log_only(tmp_path: Path) -> None:
    """A project with only a gate log (no trajectories) is discovered."""
    proj = tmp_path / "gated"
    ai = proj / "ai"
    ai.mkdir(parents=True)
    (ai / "cycle-001-gate.md").write_text("## Cycle 1: x\n", encoding="utf-8")

    names = [p.name for p in discover.discover(tmp_path)]
    assert names == ["gated"]


def test_discover_missing_root(tmp_path: Path) -> None:
    """A missing root yields an empty list, not an error."""
    assert discover.discover(tmp_path / "does-not-exist") == []


def test_discover_nested_group(tmp_path: Path) -> None:
    """Projects nested one level under a group dir are discovered (depth 2)."""
    make_project(tmp_path / "group", "nested", now=NOW, days_ago=1)

    names = [p.name for p in discover.discover(tmp_path)]
    assert names == ["nested"]


def test_is_project_predicate(tmp_path: Path) -> None:
    """is_project is True only for ai/ dirs with trajectories or a gate log."""
    ai = tmp_path / "ai"
    ai.mkdir()
    assert discover.is_project(ai) is False
    (ai / "trajectories").mkdir()
    assert discover.is_project(ai) is False  # empty trajectories dir
    (ai / "trajectories" / "trajectory_0000.json").write_text(
        '{"outcome": "x", "messages": []}', encoding="utf-8"
    )
    assert discover.is_project(ai) is True
