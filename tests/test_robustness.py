"""Robustness: fleet must not crash on degenerate project layouts.

These tests confirm that ``fleet.health.assess`` (and, where relevant,
``fleet.discover.discover``) handle edge-case layouts gracefully. Parsing is
delegated to ``fourseer`` (which skips corrupt JSON and tolerates missing
files); fleet never raises on these inputs.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path

from fleet import discover, health

NOW = datetime(2025, 6, 1, 12, 0, 0, tzinfo=timezone.utc)


def _set_mtime(path: Path, mtime: datetime) -> None:
    """Set *path*'s mtime to *mtime* (UTC)."""
    ts = mtime.timestamp()
    os.utime(path, (ts, ts))


def test_assess_trajectories_only_no_gate_log(tmp_path: Path) -> None:
    """A trajectories-only project (no gate log) assesses cleanly."""
    ai = tmp_path / "p" / "ai"
    (ai / "trajectories").mkdir(parents=True)
    traj = ai / "trajectories" / "trajectory_0000.json"
    traj.write_text(
        json.dumps({"outcome": "exit:task_complete", "messages": []}), encoding="utf-8"
    )
    _set_mtime(traj, NOW)

    h = health.assess("p", ai, now=NOW)
    assert h.health == "active"
    assert h.last_cycle == 1
    assert h.last_outcome == "exit:task_complete"
    assert h.days_since_activity == 0
    assert h.last_activity is not None


def test_assess_corrupt_trajectory_json(tmp_path: Path) -> None:
    """A corrupt trajectory JSON is skipped; a good file still yields metrics."""
    ai = tmp_path / "p" / "ai"
    (ai / "trajectories").mkdir(parents=True)
    (ai / "trajectories" / "bad.json").write_text("{not valid json", encoding="utf-8")
    good = ai / "trajectories" / "good.json"
    good.write_text(
        json.dumps({"outcome": "max_steps_reached", "messages": []}), encoding="utf-8"
    )
    _set_mtime(good, NOW)

    h = health.assess("p", ai, now=NOW)
    # Only the good file is parsed: one trajectory, its outcome, active.
    assert h.health == "active"
    assert h.last_cycle == 1
    assert h.last_outcome == "max_steps_reached"
    assert h.days_since_activity == 0


def test_assess_corrupt_only_trajectory_json(tmp_path: Path) -> None:
    """A trajectories dir with only a corrupt file assesses as dead, no crash."""
    ai = tmp_path / "p" / "ai"
    (ai / "trajectories").mkdir(parents=True)
    (ai / "trajectories" / "bad.json").write_text("{not valid json", encoding="utf-8")

    h = health.assess("p", ai, now=NOW)
    # No trajectory parses, so no trajectories -> dead; metrics are None.
    assert h.health == "dead"
    assert h.last_cycle is None
    assert h.last_outcome is None
    # The corrupt file still exists on disk, so it contributes an mtime signal.
    assert h.days_since_activity == 0


def test_assess_only_cycles_out(tmp_path: Path) -> None:
    """A project with only a cycles.out assesses as dead (no trajectories)."""
    ai = tmp_path / "p" / "ai"
    ai.mkdir(parents=True)
    co = ai / "cycles.out"
    co.write_text(
        "========== CYCLE 3  10:00:00Z ==========\n"
        "OUTER trajectory saved to: /x/trajectory_0002.json\n"
        "OUTER outcome: exit:task_complete\n",
        encoding="utf-8",
    )
    _set_mtime(co, NOW)

    h = health.assess("p", ai, now=NOW)
    assert h.health == "dead"  # no trajectories
    assert h.last_cycle == 3
    assert h.last_outcome == "exit:task_complete"
    assert h.days_since_activity == 0
    # discover does NOT find it: is_project needs trajectories or a gate log.
    assert discover.discover(tmp_path) == []


def test_assess_empty_ai_dir(tmp_path: Path) -> None:
    """An empty ai/ dir (no artifacts) assesses as dead with all-None metrics."""
    ai = tmp_path / "p" / "ai"
    ai.mkdir(parents=True)

    h = health.assess("p", ai, now=NOW)
    assert h.health == "dead"
    assert h.last_cycle is None
    assert h.last_outcome is None
    assert h.days_since_activity is None
    assert h.last_activity is None
