"""Snapshot save/load round-trip + diff-logic tests.

Covers:
  - ``save_snapshot``/``load_snapshot`` round-trip (every field preserved,
    ``last_activity`` as a ``datetime``, ``None`` fields stay ``None``).
  - ``load_snapshot`` error paths (``FileNotFoundError`` + malformed
    ``ValueError``) and the non-dict-entry filter.
  - ``snapshot_diff`` added/removed/changed/unchanged classification, the
    ``_field_changes`` detail strings (cycle/outcome/health/issues), the
    intentional exclusion of ``days_since_activity``/``last_activity``, and
    name-sorted output.
  - ``render_diff`` markdown table (unchanged rows dropped, ``(no changes)``
    sentinel, empty-detail ``-`` fallback).
"""

from __future__ import annotations

import json
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from fleet import discover, gittest
from fleet.gittest import EMPTY_STATE, GitState
from fleet.health import ProjectHealth
from fleet.snapshot import (
    DiffRow,
    Snapshot,
    _field_changes,
    load_snapshot,
    render_diff,
    save_snapshot,
    snapshot_diff,
)
from tests.test_integration_v2 import _assess_v2_root, _build_v2_root

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


def _row(
    name: str = "alpha",
    *,
    last_cycle: int | None = 5,
    last_outcome: str | None = "exit:task_complete",
    days_since_activity: int | None = 1,
    open_issues: int = 3,
    health: str = "active",
    last_activity: datetime | None = NOW,
) -> ProjectHealth:
    """Build a ``ProjectHealth`` with per-field overrides for diff tests."""
    return ProjectHealth(
        name=name,
        last_cycle=last_cycle,
        last_outcome=last_outcome,
        days_since_activity=days_since_activity,
        open_issues=open_issues,
        health=health,
        last_activity=last_activity,
    )


def _v2_row(name: str = "alpha", *, health_v2: str | None = None, **kw) -> ProjectHealth:
    """Build a ``ProjectHealth`` with a v2 class (defaults to ``None``)."""
    return replace(_row(name, **kw), health_v2=health_v2)


# ---------------------------------------------------------------------------
# save / load round-trip
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# load_snapshot error paths
# ---------------------------------------------------------------------------


def test_load_snapshot_missing_file(tmp_path: Path) -> None:
    """A missing file raises FileNotFoundError naming the path."""
    missing = tmp_path / "missing.json"
    with pytest.raises(FileNotFoundError) as exc:
        load_snapshot(missing)
    assert str(missing) in str(exc.value)


def test_load_snapshot_malformed_list(tmp_path: Path) -> None:
    """A top-level JSON list (not a dict) raises ValueError."""
    p = tmp_path / "bad.json"
    p.write_text("[1, 2, 3]", encoding="utf-8")
    with pytest.raises(ValueError):
        load_snapshot(p)


def test_load_snapshot_malformed_missing_projects(tmp_path: Path) -> None:
    """A dict lacking the 'projects' key raises ValueError."""
    p = tmp_path / "bad.json"
    p.write_text('{"created": "2025-06-01T12:00:00+00:00"}', encoding="utf-8")
    with pytest.raises(ValueError):
        load_snapshot(p)


def test_load_snapshot_skips_non_dict_entries(tmp_path: Path) -> None:
    """Non-dict entries in 'projects' are skipped, not raised on."""
    p = tmp_path / "mixed.json"
    doc = {
        "created": "2025-06-01T12:00:00+00:00",
        "projects": [
            "not-a-dict",
            {
                "name": "alpha",
                "last_cycle": 1,
                "last_outcome": "x",
                "days_since_activity": 1,
                "open_issues": 0,
                "health": "active",
                "last_activity": None,
            },
        ],
    }
    p.write_text(json.dumps(doc), encoding="utf-8")
    snap = load_snapshot(p)
    assert [h.name for h in snap.projects] == ["alpha"]


# ---------------------------------------------------------------------------
# snapshot_diff classification
# ---------------------------------------------------------------------------


def test_snapshot_diff_added() -> None:
    """A project in current but not the snapshot is 'added'."""
    snap = Snapshot(created=NOW, projects=[])
    current = [_row("alpha")]
    rows = snapshot_diff(snap, current)
    assert rows == [DiffRow(name="alpha", status="added", detail="new project")]


def test_snapshot_diff_removed() -> None:
    """A project in the snapshot but not current is 'removed'."""
    snap = Snapshot(created=NOW, projects=[_row("alpha")])
    current: list[ProjectHealth] = []
    rows = snapshot_diff(snap, current)
    assert rows == [DiffRow(name="alpha", status="removed", detail="no longer discovered")]


def test_snapshot_diff_unchanged() -> None:
    """A project identical in both is 'unchanged' with an empty detail."""
    snap = Snapshot(created=NOW, projects=[_row("alpha")])
    current = [_row("alpha")]
    rows = snapshot_diff(snap, current)
    assert rows == [DiffRow(name="alpha", status="unchanged", detail="")]


@pytest.mark.parametrize(
    ("field", "snap_val", "cur_val", "frag"),
    [
        ("last_cycle", 5, 6, "cycle 5->6"),
        (
            "last_outcome",
            "exit:task_complete",
            "timeout",
            "outcome exit:task_complete->timeout",
        ),
        ("health", "active", "stalled", "health active->stalled"),
        ("open_issues", 3, 4, "issues 3->4"),
    ],
)
def test_snapshot_diff_changed_single_field(
    field: str, snap_val: object, cur_val: object, frag: str
) -> None:
    """A single differing tracked field yields 'changed' with that fragment."""
    snap = Snapshot(created=NOW, projects=[_row("alpha", **{field: snap_val})])
    current = [_row("alpha", **{field: cur_val})]
    rows = snapshot_diff(snap, current)
    assert rows == [DiffRow(name="alpha", status="changed", detail=frag)]


def test_snapshot_diff_multiple_fields() -> None:
    """Several differing fields are comma-joined in the detail string."""
    snap = Snapshot(
        created=NOW,
        projects=[
            _row(
                "alpha",
                last_cycle=5,
                last_outcome="exit:task_complete",
                health="active",
                open_issues=3,
            )
        ],
    )
    current = [
        _row(
            "alpha",
            last_cycle=6,
            last_outcome="timeout",
            health="stalled",
            open_issues=4,
        )
    ]
    rows = snapshot_diff(snap, current)
    assert rows[0].status == "changed"
    assert rows[0].detail == (
        "cycle 5->6, outcome exit:task_complete->timeout, "
        "health active->stalled, issues 3->4"
    )


def test_snapshot_diff_ignores_days_and_last_activity() -> None:
    """days_since_activity / last_activity are intentionally not compared."""
    snap = Snapshot(
        created=NOW,
        projects=[_row("alpha", days_since_activity=1, last_activity=NOW)],
    )
    current = [
        _row("alpha", days_since_activity=9, last_activity=NOW - timedelta(days=8))
    ]
    rows = snapshot_diff(snap, current)
    assert rows == [DiffRow(name="alpha", status="unchanged", detail="")]


def test_snapshot_diff_sorted_by_name() -> None:
    """Rows are returned sorted by project name."""
    snap = Snapshot(created=NOW, projects=[_row("zeta"), _row("alpha")])
    current = [_row("alpha"), _row("mike"), _row("zeta")]
    rows = snapshot_diff(snap, current)
    assert [r.name for r in rows] == ["alpha", "mike", "zeta"]
    by = {r.name: r for r in rows}
    assert by["mike"].status == "added"
    assert by["alpha"].status == "unchanged"
    assert by["zeta"].status == "unchanged"


# ---------------------------------------------------------------------------
# _field_changes
# ---------------------------------------------------------------------------


def test_field_changes_all_four_fields() -> None:
    """_field_changes lists each differing tracked field in order."""
    s = _row(
        "alpha",
        last_cycle=5,
        last_outcome="exit:task_complete",
        health="active",
        open_issues=3,
    )
    c = _row(
        "alpha",
        last_cycle=6,
        last_outcome="timeout",
        health="stalled",
        open_issues=4,
    )
    assert _field_changes(s, c) == [
        "cycle 5->6",
        "outcome exit:task_complete->timeout",
        "health active->stalled",
        "issues 3->4",
    ]


def test_field_changes_empty_when_identical() -> None:
    """Identical rows produce no change fragments."""
    assert _field_changes(_row("alpha"), _row("alpha")) == []


# ---------------------------------------------------------------------------
# render_diff
# ---------------------------------------------------------------------------


def test_render_diff_mixed() -> None:
    """render_diff drops unchanged rows and renders the rest in order."""
    rows = [
        DiffRow(name="alpha", status="changed", detail="health active->stalled"),
        DiffRow(name="beta", status="unchanged"),
        DiffRow(name="delta", status="added", detail="new project"),
        DiffRow(name="gamma", status="removed", detail="no longer discovered"),
    ]
    out = render_diff(rows)
    assert out == (
        "| Project | Status | Detail |\n"
        "|---|---|---|\n"
        "| alpha | changed | health active->stalled |\n"
        "| delta | added | new project |\n"
        "| gamma | removed | no longer discovered |"
    )
    assert "beta" not in out


def test_render_diff_no_changes() -> None:
    """Only-unchanged rows render the single '(no changes)' row."""
    rows = [
        DiffRow(name="alpha", status="unchanged"),
        DiffRow(name="beta", status="unchanged"),
    ]
    out = render_diff(rows)
    assert out == (
        "| Project | Status | Detail |\n"
        "|---|---|---|\n"
        "| (no changes) | - | - |"
    )


def test_render_diff_empty_list() -> None:
    """An empty row list also renders the '(no changes)' row."""
    out = render_diff([])
    assert out == (
        "| Project | Status | Detail |\n"
        "|---|---|---|\n"
        "| (no changes) | - | - |"
    )


def test_render_diff_empty_detail_renders_dash() -> None:
    """A row with an empty detail renders '-' in the Detail column."""
    rows = [DiffRow(name="alpha", status="changed", detail="")]
    out = render_diff(rows)
    assert "| alpha | changed | - |" in out


# ---------------------------------------------------------------------------
# v2 snapshot shape (Cycle 18)
# ---------------------------------------------------------------------------


def test_snapshot_v2_round_trip(tmp_path: Path) -> None:
    """save_snapshot(git_states=...) stores a health_v2 per row; load round-trips it.

    The git_states mapping classifies the three rows stranded / paused / dead;
    the v1 ``health`` field is preserved alongside.
    """
    rows = [
        _row("alpha", days_since_activity=1, last_outcome="max_steps_reached", health="active"),
        _row("beta", days_since_activity=1, last_outcome="exit:task_complete", health="active"),
        _row("gamma", days_since_activity=40, last_outcome="timeout", health="dead"),
    ]
    gs = {
        "alpha": GitState(("build42/x",), 2),  # unmerged build branch -> stranded
        "beta": EMPTY_STATE,  # recent + done -> paused
        "gamma": EMPTY_STATE,  # 40d + nothing in flight -> dead
    }
    path = save_snapshot(rows, tmp_path / "snap.json", git_states=gs)
    snap = load_snapshot(path)

    by = {h.name: h for h in snap.projects}
    assert by["alpha"].health_v2 == "stranded"
    assert by["beta"].health_v2 == "paused"
    assert by["gamma"].health_v2 == "dead"
    # The v1 health field is preserved alongside the v2 class.
    assert by["alpha"].health == "active"
    assert by["beta"].health == "active"
    assert by["gamma"].health == "dead"


def test_snapshot_v2_none_without_git_states(tmp_path: Path) -> None:
    """save_snapshot without git_states leaves every health_v2 as None."""
    rows = [_row("alpha"), _row("beta"), _row("gamma")]
    path = save_snapshot(rows, tmp_path / "snap.json")
    snap = load_snapshot(path)
    assert [h.health_v2 for h in snap.projects] == [None, None, None]


def test_snapshot_old_v1_still_loads(tmp_path: Path) -> None:
    """A hand-written v1 snapshot (no health_v2 key) loads with health_v2=None."""
    doc = {
        "created": "2025-06-01T12:00:00+00:00",
        "projects": [
            {
                "name": "alpha",
                "last_cycle": 5,
                "last_outcome": "exit:task_complete",
                "days_since_activity": 1,
                "open_issues": 3,
                "health": "active",
                "last_activity": "2025-06-01T12:00:00+00:00",
            }
        ],
    }
    p = tmp_path / "v1.json"
    p.write_text(json.dumps(doc), encoding="utf-8")
    snap = load_snapshot(p)

    got = snap.projects[0]
    assert got.health_v2 is None
    # The other seven fields are intact.
    assert got.name == "alpha"
    assert got.last_cycle == 5
    assert got.last_outcome == "exit:task_complete"
    assert got.days_since_activity == 1
    assert got.open_issues == 3
    assert got.health == "active"
    assert got.last_activity == NOW


def test_snapshot_diff_surfaces_v2_change() -> None:
    """A v2-class change (same v1 health) is reported as 'changed'."""
    snap = Snapshot(created=NOW, projects=[_v2_row("alpha", health_v2="stranded")])
    current = [_v2_row("alpha", health_v2="paused")]
    rows = snapshot_diff(snap, current)
    assert rows == [
        DiffRow(name="alpha", status="changed", detail="health_v2 stranded->paused")
    ]


def test_snapshot_diff_unchanged_when_v2_same() -> None:
    """Identical rows (same v2 class) are 'unchanged'."""
    snap = Snapshot(created=NOW, projects=[_v2_row("alpha", health_v2="stranded")])
    current = [_v2_row("alpha", health_v2="stranded")]
    rows = snapshot_diff(snap, current)
    assert rows == [DiffRow(name="alpha", status="unchanged", detail="")]


def test_snapshot_diff_v2_none_to_set() -> None:
    """A None -> class v2 transition renders as 'health_v2 --><class>'."""
    snap = Snapshot(created=NOW, projects=[_v2_row("alpha", health_v2=None)])
    current = [_v2_row("alpha", health_v2="stranded")]
    rows = snapshot_diff(snap, current)
    assert rows == [
        DiffRow(name="alpha", status="changed", detail="health_v2 -->stranded")
    ]


def test_snapshot_v2_canary_classes(tmp_path: Path) -> None:
    """The three canary shapes classify stranded / paused / dead at the snapshot layer.

    Builds the real git-repo fixture root (Cycle 17 pattern), assesses each
    project, reads the git state, and saves a snapshot carrying the v2 class.
    """
    _build_v2_root(tmp_path)
    projects = discover.discover(tmp_path)
    git_states = {p.name: gittest.read_gitstate(p.path) for p in projects}
    assessed = _assess_v2_root(tmp_path)

    path = save_snapshot(assessed, tmp_path / "snap.json", git_states=git_states)
    snap = load_snapshot(path)

    by = {h.name: h for h in snap.projects}
    assert by["alloc-pipeline"].health_v2 == "stranded"
    assert by["deepseek-deharness"].health_v2 == "paused"
    assert by["gamma"].health_v2 == "dead"
