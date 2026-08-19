"""Tests for fleet.health (metrics extraction + classification)."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from unittest import mock

from fleet import health
from tests._fixtures import make_project

NOW = datetime(2025, 6, 1, 12, 0, 0, tzinfo=timezone.utc)


def test_classify_health_boundaries() -> None:
    """The active/stalled/dead thresholds are exactly 7 and 30 days."""
    assert health.classify_health(0, True) == "active"
    assert health.classify_health(7, True) == "active"
    assert health.classify_health(8, True) == "stalled"
    assert health.classify_health(30, True) == "stalled"
    assert health.classify_health(31, True) == "dead"
    # No trajectories is always dead, regardless of recency.
    assert health.classify_health(0, False) == "dead"
    assert health.classify_health(5, False) == "dead"


def test_classify_health_no_activity() -> None:
    """A None day count is stalled when trajectories exist, dead otherwise."""
    assert health.classify_health(None, True) == "stalled"
    assert health.classify_health(None, False) == "dead"


def test_assess_active_project(tmp_path: Path) -> None:
    """A project active 1 day ago classifies as active with correct metrics."""
    ai = make_project(
        tmp_path,
        "alpha",
        now=NOW,
        days_ago=1,
        outcome="exit:task_complete",
        n_traj=3,
        cycles_out=(
            "========== CYCLE 1  10:00:00Z ==========\n"
            "OUTER trajectory saved to: /x/trajectory_0000.json\n"
            "OUTER outcome: exit:task_complete\n"
            "========== CYCLE 2  11:00:00Z ==========\n"
            "OUTER trajectory saved to: /x/trajectory_0001.json\n"
            "OUTER outcome: max_steps_reached\n"
        ),
    )
    with mock.patch.object(health, "count_open_issues", return_value=4):
        h = health.assess("alpha", ai, repo="owner/alpha", now=NOW)

    assert h.health == "active"
    assert h.last_cycle == 2
    assert h.last_outcome == "max_steps_reached"
    assert h.days_since_activity == 1
    assert h.open_issues == 4


def test_assess_dead_no_trajectories(tmp_path: Path) -> None:
    """A project with only a gate log (no trajectories) is dead."""
    proj = tmp_path / "gated"
    ai = proj / "ai"
    ai.mkdir(parents=True)
    (ai / "cycle-001-gate.md").write_text("## Cycle 1: x\n", encoding="utf-8")

    with mock.patch.object(health, "count_open_issues", return_value=0):
        h = health.assess("gated", ai, now=NOW)

    assert h.health == "dead"
    assert h.last_cycle == 1  # from the gate log cycle block
    assert h.last_outcome is None


def test_assess_stalled(tmp_path: Path) -> None:
    """A project idle 20 days classifies as stalled."""
    ai = make_project(tmp_path, "beta", now=NOW, days_ago=20, outcome="max_steps_reached")
    with mock.patch.object(health, "count_open_issues", return_value=0):
        h = health.assess("beta", ai, now=NOW)
    assert h.health == "stalled"
    assert h.days_since_activity == 20


def test_count_open_issues_no_repo() -> None:
    """count_open_issues returns 0 when no repo is given."""
    assert health.count_open_issues(None) == 0
    assert health.count_open_issues("") == 0


def test_count_open_issues_gh_failure() -> None:
    """count_open_issues returns 0 when gh is unavailable or errors."""
    with mock.patch.object(health.subprocess, "run", side_effect=OSError("no gh")):
        assert health.count_open_issues("owner/repo") == 0
    with mock.patch.object(
        health.subprocess, "run", return_value=mock.Mock(returncode=1, stdout="")
    ):
        assert health.count_open_issues("owner/repo") == 0


def test_count_open_issues_counts_lines() -> None:
    """count_open_issues counts non-empty gh output lines."""
    proc = mock.Mock(returncode=0, stdout="1\topen\ttitle\n2\topen\ttitle2\n")
    with mock.patch.object(health.subprocess, "run", return_value=proc):
        assert health.count_open_issues("owner/repo") == 2
