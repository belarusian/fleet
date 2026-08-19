"""Snapshot save/load round-trip test.

Confirms that `fleet.snapshot.save_snapshot`/`load_snapshot` round-trips a
`ProjectHealth` list to/from JSON with every field preserved: `last_activity`
survives as a `datetime`, and `None` fields stay `None`.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from fleet.health import ProjectHealth
from fleet.snapshot import load_snapshot, save_snapshot

NOW = datetime(2025, 6, 1, 12, 0, 0, tzinfo=timezone.utc)


def _full_row() -> ProjectHealth:
    """A fully-populated health row (datetime last_activity, no Nones)."""
    return ProjectHealth(
        name="alpha",
        last_cycle=5,
        last_outcome="exit:task_complete",
        days_since_activity=1,
        open_issues=3,
        health="active",
        last_activity=NOW,
    )


def _none_row() -> ProjectHealth:
    """A row whose optional fields are all None (no activity signal)."""
    return ProjectHealth(
        name="gamma",
        last_cycle=None,
        last_outcome=None,
        days_since_activity=None,
        open_issues=0,
        health="dead",
        last_activity=None,
    )


def test_snapshot_round_trip_preserves_fields(tmp_path: Path) -> None:
    """save -> load preserves every field of a fully-populated row."""
    path = save_snapshot([_full_row()], tmp_path / "snap.json")
    snap = load_snapshot(path)

    assert len(snap.projects) == 1
    got = snap.projects[0]
    assert got.name == "alpha"
    assert got.last_cycle == 5
    assert got.last_outcome == "exit:task_complete"
    assert got.days_since_activity == 1
    assert got.open_issues == 3
    assert got.health == "active"
    # last_activity survives as a datetime equal to the original.
    assert isinstance(got.last_activity, datetime)
    assert got.last_activity == NOW


def test_snapshot_round_trip_preserves_none_fields(tmp_path: Path) -> None:
    """save -> load keeps None fields None (no coercion to strings/0)."""
    path = save_snapshot([_none_row()], tmp_path / "snap.json")
    snap = load_snapshot(path)

    got = snap.projects[0]
    assert got.name == "gamma"
    assert got.last_cycle is None
    assert got.last_outcome is None
    assert got.days_since_activity is None
    assert got.open_issues == 0
    assert got.health == "dead"
    assert got.last_activity is None


def test_snapshot_round_trip_multiple_rows(tmp_path: Path) -> None:
    """A mixed list round-trips with order and per-row fields intact."""
    rows = [_full_row(), _none_row()]
    path = save_snapshot(rows, tmp_path / "snap.json")
    snap = load_snapshot(path)

    assert [h.name for h in snap.projects] == ["alpha", "gamma"]
    assert snap.projects[0] == _full_row()
    assert snap.projects[1] == _none_row()
