"""Tests for fleet.health (metrics extraction + classification)."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from unittest import mock

from fleet import health
from fleet.gittest import GitState
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


def test_assess_stalled_dead_boundary(tmp_path: Path) -> None:
    """The stalled->dead boundary is exercised end-to-end through assess.

    30 days idle is still stalled (<= STALLED_MAX_DAYS); 31 days is dead.
    This pins the exact boundary at the assess level, not just classify_health.
    """
    ai30 = make_project(tmp_path, "edge30", now=NOW, days_ago=30, outcome="max_steps_reached")
    with mock.patch.object(health, "count_open_issues", return_value=0):
        h30 = health.assess("edge30", ai30, now=NOW)
    assert h30.health == "stalled"
    assert h30.days_since_activity == 30

    ai31 = make_project(tmp_path, "edge31", now=NOW, days_ago=31, outcome="max_steps_reached")
    with mock.patch.object(health, "count_open_issues", return_value=0):
        h31 = health.assess("edge31", ai31, now=NOW)
    assert h31.health == "dead"
    assert h31.days_since_activity == 31


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


def test_health_gate_log_outcome(tmp_path: Path) -> None:
    """A gate-only project derives last_outcome from the gate log's last block."""
    proj = tmp_path / "gated"
    ai = proj / "ai"
    ai.mkdir(parents=True)
    (ai / "cycle-001-gate.md").write_text(
        "## Cycle 1: Foundations\n"
        "**Date:** 2025-06-01\n"
        "### Results\n"
        "| Check | Before | After |\n"
        "|---|---|---|\n"
        "| Gate (build+test+lint) | red | green |\n"
        "| Merged on main | - | abc1234 |\n",
        encoding="utf-8",
    )
    with mock.patch.object(health, "count_open_issues", return_value=0):
        h = health.assess("gated", ai, now=NOW)
    assert h.last_cycle == 1
    assert h.last_outcome == "gate:green"
    assert h.health == "dead"  # no trajectories


def test_health_gate_log_merged_only(tmp_path: Path) -> None:
    """A gate log with a merged row but no gate row maps to 'merged'."""
    proj = tmp_path / "gated2"
    ai = proj / "ai"
    ai.mkdir(parents=True)
    (ai / "cycle-001-gate.md").write_text(
        "## Cycle 2: More\n"
        "### Results\n"
        "| Check | Before | After |\n"
        "|---|---|---|\n"
        "| Merged on main | - | def5678 |\n",
        encoding="utf-8",
    )
    with mock.patch.object(health, "count_open_issues", return_value=0):
        h = health.assess("gated2", ai, now=NOW)
    assert h.last_cycle == 2
    assert h.last_outcome == "merged"


def test_health_gate_log_missing_stays_none(tmp_path: Path) -> None:
    """A gate log with no Results table keeps last_outcome None."""
    proj = tmp_path / "gated3"
    ai = proj / "ai"
    ai.mkdir(parents=True)
    (ai / "cycle-001-gate.md").write_text("## Cycle 1: x\n", encoding="utf-8")
    with mock.patch.object(health, "count_open_issues", return_value=0):
        h = health.assess("gated3", ai, now=NOW)
    assert h.last_cycle == 1
    assert h.last_outcome is None


def test_health_last_outcome_follows_mtime(tmp_path: Path) -> None:
    """last_outcome comes from the newest-mtime trajectory, not filename order."""
    import json
    import os

    proj = tmp_path / "beta"
    ai = proj / "ai"
    (ai / "trajectories").mkdir(parents=True)
    p0 = ai / "trajectories" / "trajectory_0000.json"
    p1 = ai / "trajectories" / "trajectory_0001.json"
    p0.write_text(json.dumps({"outcome": "exit:task_complete", "messages": []}), encoding="utf-8")
    p1.write_text(json.dumps({"outcome": "max_steps_reached", "messages": []}), encoding="utf-8")
    # Make the higher-numbered file OLDER so filename order and mtime disagree.
    os.utime(p0, (NOW.timestamp() - 86400, NOW.timestamp() - 86400))
    os.utime(p1, (NOW.timestamp() - 86400 * 5, NOW.timestamp() - 86400 * 5))
    with mock.patch.object(health, "count_open_issues", return_value=0):
        h = health.assess("beta", ai, now=NOW)
    # p0 is newer by mtime, so its outcome wins even though p1 has the higher name.
    assert h.last_outcome == "exit:task_complete"
    assert h.days_since_activity == 1


# --- project_health wrapper tests ---


def test_project_health_name_derivation(tmp_path: Path) -> None:
    """project_health derives the name from ai_dir.parent.name."""
    ai = make_project(tmp_path, "myproj", now=NOW, days_ago=1)
    with mock.patch.object(health, "count_open_issues", return_value=0):
        h = health.project_health(ai)
    assert h.name == "myproj"


def test_project_health_repo_passthrough(tmp_path: Path) -> None:
    """project_health passes repo_path through to assess."""
    ai = make_project(tmp_path, "myproj", now=NOW, days_ago=1)
    with mock.patch.object(health, "count_open_issues", return_value=7) as m:
        h = health.project_health(ai, repo_path="owner/myproj")
    m.assert_called_once_with("owner/myproj")
    assert h.open_issues == 7


def test_project_health_now_default(tmp_path: Path) -> None:
    """project_health does not pass a now kwarg, so assess defaults to UTC now."""
    ai = make_project(tmp_path, "myproj", now=NOW, days_ago=1)
    with mock.patch.object(health, "assess", wraps=health.assess) as m:
        with mock.patch.object(health, "count_open_issues", return_value=0):
            health.project_health(ai)
    # Verify assess was called without a 'now' keyword argument.
    _, kwargs = m.call_args
    assert "now" not in kwargs


# --- project_health classification tests (TICKET-012) ---
#
# project_health does not take a `now` argument, so it delegates to assess with
# the real UTC clock. To pin the classification deterministically we patch
# health.datetime.now to return the fixed NOW reference.


class _FakeDatetime(datetime):
    """A datetime subclass whose .now() is pinned to NOW.

    Inheriting from the real datetime keeps .fromtimestamp() (used by
    _last_activity) working; only the clock is frozen.
    """

    @classmethod
    def now(cls, tz=None):  # noqa: ARG003 - tz ignored, we always return UTC NOW
        return NOW


def _patched_now():
    """Patch health.datetime so .now() returns the fixed NOW reference."""
    return mock.patch.object(health, "datetime", _FakeDatetime)


def test_project_health_active(tmp_path: Path) -> None:
    """project_health drives an active project to health == 'active'."""
    ai = make_project(tmp_path, "activeproj", now=NOW, days_ago=1, outcome="exit:task_complete")
    with mock.patch.object(health, "count_open_issues", return_value=0), _patched_now():
        h = health.project_health(ai)
    assert h.name == "activeproj"
    assert h.health == "active"
    assert h.days_since_activity == 1


def test_project_health_stalled(tmp_path: Path) -> None:
    """project_health drives a 20-day-idle project to health == 'stalled'."""
    ai = make_project(tmp_path, "stalledproj", now=NOW, days_ago=20, outcome="max_steps_reached")
    with mock.patch.object(health, "count_open_issues", return_value=0), _patched_now():
        h = health.project_health(ai)
    assert h.name == "stalledproj"
    assert h.health == "stalled"
    assert h.days_since_activity == 20


def test_project_health_dead(tmp_path: Path) -> None:
    """project_health drives a no-trajectory project to health == 'dead'."""
    proj = tmp_path / "deadproj"
    ai = proj / "ai"
    ai.mkdir(parents=True)
    (ai / "cycle-001-gate.md").write_text("## Cycle 1: x\n", encoding="utf-8")
    with mock.patch.object(health, "count_open_issues", return_value=0), _patched_now():
        h = health.project_health(ai)
    assert h.name == "deadproj"
    assert h.health == "dead"


# --- classify_health_v2 tests (TICKET-056) ---
#
# classify_health_v2 is PURE: it takes (days, last_outcome, git_state) and
# returns one of "stranded" / "active" / "paused" / "dead" (most-severe-wins).
# Tests construct GitState(...) directly — no git subprocess, no tmp_path, no
# fourseer. The "no git" cases use the empty state GitState((), 0).

_EMPTY = GitState((), 0)


def test_v2_unmerged_branch_stranded_any_recency() -> None:
    """An unmerged build* branch is stranded regardless of recency (case 1)."""
    gs = GitState(("build9/unmerged",), 0)
    assert health.classify_health_v2(1, "exit:task_complete", gs) == "stranded"
    assert health.classify_health_v2(40, None, gs) == "stranded"


def test_v2_unpushed_commits_stranded_any_recency() -> None:
    """Unpushed commits on main are stranded regardless of recency (case 2)."""
    gs = GitState((), 3)
    assert health.classify_health_v2(1, "exit:task_complete", gs) == "stranded"
    assert health.classify_health_v2(40, None, gs) == "stranded"


def test_v2_recent_max_steps_active() -> None:
    """Recent (<=7d) + max_steps_reached, no git -> active (case 3)."""
    assert health.classify_health_v2(1, "max_steps_reached", _EMPTY) == "active"


def test_v2_stranded_beats_active() -> None:
    """Recent + unmerged branch + max_steps_reached -> stranded (case 4)."""
    gs = GitState(("build9/unmerged",), 0)
    assert health.classify_health_v2(1, "max_steps_reached", gs) == "stranded"


def test_v2_recent_task_complete_paused() -> None:
    """Recent + exit:task_complete, nothing in flight -> paused (case 5)."""
    assert health.classify_health_v2(1, "exit:task_complete", _EMPTY) == "paused"


def test_v2_recent_none_outcome_paused() -> None:
    """Recent + last_outcome None, nothing in flight -> paused (case 6)."""
    assert health.classify_health_v2(1, None, _EMPTY) == "paused"


def test_v2_old_nothing_in_flight_dead() -> None:
    """30+ days, nothing in flight -> dead (case 7)."""
    assert health.classify_health_v2(40, "exit:task_complete", _EMPTY) == "dead"
    assert health.classify_health_v2(40, None, _EMPTY) == "dead"


def test_v2_mid_band_paused() -> None:
    """8-29 days idle, nothing in flight -> paused (benign, not yet dead) (case 8)."""
    assert health.classify_health_v2(8, "exit:task_complete", _EMPTY) == "paused"
    assert health.classify_health_v2(29, None, _EMPTY) == "paused"


def test_v2_none_days_nothing_in_flight_dead() -> None:
    """days is None, nothing in flight -> dead (no activity signal) (case 9)."""
    assert health.classify_health_v2(None, "exit:task_complete", _EMPTY) == "dead"
    assert health.classify_health_v2(None, None, _EMPTY) == "dead"


def test_v2_none_days_max_steps_active() -> None:
    """days is None + max_steps_reached -> active (work in flight) (case 10)."""
    assert health.classify_health_v2(None, "max_steps_reached", _EMPTY) == "active"


def test_v2_mid_band_max_steps_active() -> None:
    """8-29 days + max_steps_reached, no git -> active (in flight, not recent) (case 11)."""
    assert health.classify_health_v2(8, "max_steps_reached", _EMPTY) == "active"
    assert health.classify_health_v2(29, "max_steps_reached", _EMPTY) == "active"


def test_v2_stranded_beats_dead() -> None:
    """Unpushed commits + 30+ days -> stranded (stranded beats dead) (case 12)."""
    gs = GitState((), 3)
    assert health.classify_health_v2(40, "exit:task_complete", gs) == "stranded"


def test_v2_boundary_7_days() -> None:
    """Boundary at 7 days: max_steps -> active, task_complete -> paused (case 13)."""
    assert health.classify_health_v2(7, "max_steps_reached", _EMPTY) == "active"
    assert health.classify_health_v2(7, "exit:task_complete", _EMPTY) == "paused"


def test_v2_boundary_30_days() -> None:
    """Boundary at 30 days: nothing in flight -> dead; 29 days -> paused (case 14).

    Note the deliberate divergence from v1: v1 classify_health calls 30 days
    "stalled" (its dead boundary is > 30), while v2 calls 30 days "dead" (its
    dead boundary is >= 30). Do not unify the two.
    """
    assert health.classify_health_v2(30, "exit:task_complete", _EMPTY) == "dead"
    assert health.classify_health_v2(29, "exit:task_complete", _EMPTY) == "paused"


def test_v2_canary_alloc_pipeline_stranded() -> None:
    """Canary (alloc-pipeline shape): unmerged build42 + unpushed -> stranded (case 15)."""
    gs = GitState(("build42/model-persistence-rebalance",), 3)
    assert health.classify_health_v2(1, "max_steps_reached", gs) == "stranded"


def test_v2_canary_deepseek_deharness_paused() -> None:
    """Canary (deepseek-deharness shape): recent + task_complete -> paused (case 16)."""
    assert health.classify_health_v2(1, "exit:task_complete", _EMPTY) == "paused"
