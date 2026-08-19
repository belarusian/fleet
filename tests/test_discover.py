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


# --- edge-case hardening tests ---


def test_discover_empty_root(tmp_path: Path) -> None:
    """An empty root directory yields an empty list."""
    assert discover.discover(tmp_path) == []


def test_discover_root_with_only_non_project_dirs(tmp_path: Path) -> None:
    """A root with only non-project directories yields an empty list."""
    (tmp_path / "docs").mkdir()
    (tmp_path / "scripts").mkdir()
    (tmp_path / "notes").mkdir()
    # A dir with ai/ but no trajectories and no gate log is not a project.
    (tmp_path / "emptyproj" / "ai").mkdir(parents=True)
    assert discover.discover(tmp_path) == []


def test_discover_gate_log_without_cycle_block(tmp_path: Path) -> None:
    """A gate log file that exists but has no '## Cycle' block is still a project."""
    proj = tmp_path / "gated"
    ai = proj / "ai"
    ai.mkdir(parents=True)
    # Gate log with content but no "## Cycle N" header.
    (ai / "cycle-001-gate.md").write_text(
        "# Gate Log\n\nSome free-form text without any cycle blocks.\n",
        encoding="utf-8",
    )
    found = discover.discover(tmp_path)
    assert len(found) == 1
    assert found[0].name == "gated"


def _gate_log_md(cycle_no: int, title: str, gate_after: str) -> str:
    """Build a minimal gate-log markdown block with a single Results row."""
    rows = [
        f"## Cycle {cycle_no}: {title}",
        "### Results",
        "| Check | Before | After |",
        "|---|---|---|",
        f"| Gate (build+test+lint) | red | {gate_after} |",
    ]
    return "\n".join(rows) + "\n"


def test_discover_multiple_gate_logs_prefers_cycle_001(tmp_path: Path) -> None:
    """When multiple gate logs exist, fourseer prefers the one with cycle-001."""
    import fourseer

    proj = tmp_path / "multi"
    ai = proj / "ai"
    ai.mkdir(parents=True)
    # Two gate logs: one with cycle-001 in the name, one without.
    (ai / "cycle-002-gate.md").write_text(
        _gate_log_md(2, "Later", "red"), encoding="utf-8"
    )
    (ai / "cycle-001-gate.md").write_text(
        _gate_log_md(1, "Earlier", "green"), encoding="utf-8"
    )
    # fourseer.load_run should prefer cycle-001.
    run = fourseer.load_run(ai)
    assert len(run.gate_log.cycles) == 1
    assert run.gate_log.cycles[0].cycle_no == 1
    assert run.gate_log.cycles[0].gate_after == "green"


def test_discover_trajectory_dir_with_single_file(tmp_path: Path) -> None:
    """A trajectories dir with exactly one JSON file is a valid project."""
    import json

    proj = tmp_path / "single"
    ai = proj / "ai"
    (ai / "trajectories").mkdir(parents=True)
    (ai / "trajectories" / "trajectory_0000.json").write_text(
        json.dumps({"outcome": "exit:task_complete", "messages": []}),
        encoding="utf-8",
    )
    found = discover.discover(tmp_path)
    assert len(found) == 1
    assert found[0].name == "single"
    assert found[0].ai_dir == ai


def test_project_ref_alias() -> None:
    """ProjectRef is an alias for Project."""
    assert discover.ProjectRef is discover.Project
