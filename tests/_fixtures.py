"""Shared test fixtures: build fake project AI directories on disk.

These helpers write minimal, realistic four-pipeline artifacts (a
``trajectories/`` dir with JSON, a ``cycles.out``, and a gate log) into a
temporary root so the fleet scanners can be exercised end-to-end without
touching the real ``~/AI`` tree.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path


def _write_trajectory(ai: Path, name: str, outcome: str, mtime: datetime) -> None:
    """Write one trajectory JSON under *ai/trajectories* with a fixed mtime."""
    traj_dir = ai / "trajectories"
    traj_dir.mkdir(parents=True, exist_ok=True)
    path = traj_dir / name
    path.write_text(
        json.dumps({"outcome": outcome, "messages": [{"role": "assistant", "content": "hi"}]}),
        encoding="utf-8",
    )
    _set_mtime(path, mtime)


def _set_mtime(path: Path, mtime: datetime) -> None:
    """Set *path*'s mtime to *mtime* (UTC)."""
    ts = mtime.timestamp()
    import os

    os.utime(path, (ts, ts))


def make_project(
    root: Path,
    name: str,
    *,
    now: datetime,
    days_ago: float,
    outcome: str = "exit:task_complete",
    n_traj: int = 1,
    cycles_out: str | None = None,
    gate_log: str | None = None,
) -> Path:
    """Create a fake project under *root* and return its ``ai/`` dir.

    Parameters
    ----------
    root:
        The scan root to place the project under.
    name:
        The project directory name.
    now:
        The reference "now" (UTC) used to back-date the activity.
    days_ago:
        How many days before *now* the most recent activity occurred.
    outcome:
        The trajectory outcome string.
    n_traj:
        Number of trajectory files to write.
    cycles_out:
        Optional ``cycles.out`` text to write.
    gate_log:
        Optional gate-log markdown to write.
    """
    proj = root / name
    ai = proj / "ai"
    ai.mkdir(parents=True, exist_ok=True)

    activity_time = now - timedelta(days=days_ago)
    for i in range(n_traj):
        _write_trajectory(ai, f"trajectory_{i:04d}.json", outcome, activity_time)

    if cycles_out is not None:
        co = ai / "cycles.out"
        co.write_text(cycles_out, encoding="utf-8")
        _set_mtime(co, activity_time)

    if gate_log is not None:
        gl = ai / "cycle-001-gate.md"
        gl.write_text(gate_log, encoding="utf-8")
        _set_mtime(gl, activity_time)

    return ai
