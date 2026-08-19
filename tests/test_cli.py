"""CLI `status` wiring test (preview for the CLI phase).

Confirms that `fleet.cli` `status` actually composes discover -> assess ->
render_portfolio and honors `--filter` (active/stalled/dead/all). The clock is
pinned (patch `health.datetime` with a `datetime` subclass whose `now()`
returns the fixed NOW, keeping `fromtimestamp` working) and the open-issue
lookup is patched so the output is deterministic.
"""

from __future__ import annotations

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock

from fleet import cli, health, report, snapshot
from tests._fixtures import make_project

NOW = datetime(2025, 6, 1, 12, 0, 0, tzinfo=timezone.utc)


class _FakeDatetime(datetime):
    """A datetime subclass whose .now() is pinned to NOW (keeps fromtimestamp)."""

    @classmethod
    def now(cls, tz=None):  # noqa: ARG003 - tz ignored, always return UTC NOW
        return NOW


def _issues(repo: str | None) -> int:
    """Deterministic open-issue counts keyed by the owner/repo string."""
    return {"owner/alpha": 3, "owner/beta": 1, "owner/gamma": 0}.get(repo or "", 0)


def _build_root(root: Path) -> None:
    """Three projects in distinct health states (days_ago 1/20/40)."""
    make_project(root, "alpha", now=NOW, days_ago=1, n_traj=3, outcome="exit:task_complete")
    make_project(root, "beta", now=NOW, days_ago=20, n_traj=2, outcome="max_steps_reached")
    make_project(root, "gamma", now=NOW, days_ago=40, n_traj=1, outcome="timeout")


def _assess_root(root: Path) -> list[health.ProjectHealth]:
    """Assess every discovered project exactly as the CLI does (no repo).

    The CLI's `_assess_all` calls `assess(name, ai_dir)` with no `repo`, so
    `count_open_issues(None)` returns 0 for every row. Mirroring that keeps the
    expected table identical to what `status` prints.
    """
    from fleet import discover

    projects = discover.discover(root)
    with mock.patch.object(health, "count_open_issues", side_effect=_issues):
        return [health.assess(p.name, p.ai_dir, now=NOW) for p in projects]


def _run_status(root: Path, *extra: str, capsys) -> str:
    """Run `fleet status --root <root> [extra...]` and return captured stdout."""
    argv = ["status", "--root", str(root), *extra]
    with mock.patch.object(health, "count_open_issues", side_effect=_issues), mock.patch.object(
        health, "datetime", _FakeDatetime
    ):
        rc = cli.main(argv)
    assert rc == 0
    return capsys.readouterr().out


def test_cli_status_matches_render_portfolio(tmp_path: Path, capsys) -> None:
    """`status` stdout equals render_portfolio(assessed) for a known root."""
    _build_root(tmp_path)
    assessed = _assess_root(tmp_path)

    out = _run_status(tmp_path, capsys=capsys)
    assert out == report.render_portfolio(assessed) + "\n"


def test_cli_status_filter_active(tmp_path: Path, capsys) -> None:
    """`--filter active` yields only the active project's row."""
    _build_root(tmp_path)
    assessed = _assess_root(tmp_path)
    expected = report.render_portfolio([h for h in assessed if h.health == "active"])

    out = _run_status(tmp_path, "--filter", "active", capsys=capsys)
    assert out == expected + "\n"
    assert "alpha" in out
    assert "beta" not in out
    assert "gamma" not in out


def test_cli_status_filter_stalled(tmp_path: Path, capsys) -> None:
    """`--filter stalled` yields only the stalled project's row."""
    _build_root(tmp_path)
    assessed = _assess_root(tmp_path)
    expected = report.render_portfolio([h for h in assessed if h.health == "stalled"])

    out = _run_status(tmp_path, "--filter", "stalled", capsys=capsys)
    assert out == expected + "\n"
    assert "beta" in out
    assert "alpha" not in out
    assert "gamma" not in out


def test_cli_status_filter_dead(tmp_path: Path, capsys) -> None:
    """`--filter dead` yields only the dead project's row."""
    _build_root(tmp_path)
    assessed = _assess_root(tmp_path)
    expected = report.render_portfolio([h for h in assessed if h.health == "dead"])

    out = _run_status(tmp_path, "--filter", "dead", capsys=capsys)
    assert out == expected + "\n"
    assert "gamma" in out
    assert "alpha" not in out
    assert "beta" not in out


def test_cli_status_filter_all(tmp_path: Path, capsys) -> None:
    """`--filter all` (the default) yields every row."""
    _build_root(tmp_path)
    assessed = _assess_root(tmp_path)

    out = _run_status(tmp_path, "--filter", "all", capsys=capsys)
    assert out == report.render_portfolio(assessed) + "\n"
    for name in ("alpha", "beta", "gamma"):
        assert name in out


# ---------------------------------------------------------------------------
# CLI `diff` subcommand
# ---------------------------------------------------------------------------


def _assess_root_no_repo(root: Path) -> list[health.ProjectHealth]:
    """Assess every discovered project exactly as the CLI does (no repo).

    The CLI's ``_assess_all`` calls ``assess(name, ai_dir)`` with no ``repo``,
    so ``count_open_issues(None)`` returns 0 for every row. Mirroring that
    (omitting ``repo``) keeps the expected diff identical to what ``diff``
    prints — passing a repo would make the open-issue column diverge.
    """
    from fleet import discover

    projects = discover.discover(root)
    with mock.patch.object(health, "count_open_issues", side_effect=_issues):
        return [health.assess(p.name, p.ai_dir, now=NOW) for p in projects]


def _run_diff(root: Path, snap_path: Path, capsys) -> tuple[int, str, str]:
    """Run ``fleet diff --root <root> --snapshot <snap>``; return (rc, out, err)."""
    argv = ["diff", "--root", str(root), "--snapshot", str(snap_path)]
    with mock.patch.object(health, "count_open_issues", side_effect=_issues), mock.patch.object(
        health, "datetime", _FakeDatetime
    ):
        rc = cli.main(argv)
    out, err = capsys.readouterr()
    return rc, out, err


def test_cli_diff_missing_snapshot(tmp_path: Path, capsys) -> None:
    """A missing --snapshot file exits 2 with a message on stderr."""
    _build_root(tmp_path)
    missing = tmp_path / "does-not-exist.json"
    rc, out, err = _run_diff(tmp_path, missing, capsys)
    assert rc == 2
    assert "snapshot not found" in err
    assert str(missing) in err
    assert out == ""


def test_cli_diff_matches_render_diff(tmp_path: Path, capsys) -> None:
    """diff stdout equals render_diff(snapshot_diff(snap, current))."""
    _build_root(tmp_path)
    # Save a snapshot of the current (unmutated) portfolio.
    snap_path = snapshot.save_snapshot(_assess_root_no_repo(tmp_path), tmp_path / "snap.json")
    # Mutate the root so the diff is non-trivial: add a project, remove one,
    # and change one project's outcome.
    make_project(tmp_path, "delta", now=NOW, days_ago=2, n_traj=2, outcome="exit:task_complete")
    shutil.rmtree(tmp_path / "gamma")
    (tmp_path / "beta" / "ai" / "trajectories" / "trajectory_0000.json").write_text(
        json.dumps({"outcome": "timeout", "messages": []}), encoding="utf-8"
    )

    current = _assess_root_no_repo(tmp_path)
    snap = snapshot.load_snapshot(snap_path)
    expected = snapshot.render_diff(snapshot.snapshot_diff(snap, current))

    rc, out, err = _run_diff(tmp_path, snap_path, capsys)
    assert rc == 0
    assert err == ""
    assert out == expected + "\n"


def test_cli_diff_exercises_all_row_kinds(tmp_path: Path, capsys) -> None:
    """A snapshot/current pair yields added, removed, changed, unchanged rows."""
    _build_root(tmp_path)
    snap_path = snapshot.save_snapshot(_assess_root_no_repo(tmp_path), tmp_path / "snap.json")
    # Add 'delta' (added), remove 'gamma' (removed), change 'beta' outcome
    # (changed); leave 'alpha' untouched (unchanged).
    make_project(tmp_path, "delta", now=NOW, days_ago=2, n_traj=2, outcome="exit:task_complete")
    shutil.rmtree(tmp_path / "gamma")
    (tmp_path / "beta" / "ai" / "trajectories" / "trajectory_0000.json").write_text(
        json.dumps({"outcome": "timeout", "messages": []}), encoding="utf-8"
    )

    current = _assess_root_no_repo(tmp_path)
    snap = snapshot.load_snapshot(snap_path)
    rows = snapshot.snapshot_diff(snap, current)
    by = {r.name: r for r in rows}

    assert by["delta"].status == "added"
    assert by["gamma"].status == "removed"
    assert by["beta"].status == "changed"
    assert "outcome" in by["beta"].detail
    assert by["alpha"].status == "unchanged"
    # Rows are sorted by name.
    assert [r.name for r in rows] == sorted(by)

    rc, out, err = _run_diff(tmp_path, snap_path, capsys)
    assert rc == 0
    assert err == ""
    # render_diff drops the unchanged 'alpha' row.
    assert "alpha" not in out
    assert "| delta | added |" in out
    assert "| gamma | removed |" in out
    assert "| beta | changed |" in out


def test_cli_diff_no_changes(tmp_path: Path, capsys) -> None:
    """An unchanged portfolio renders the single '(no changes)' row."""
    _build_root(tmp_path)
    snap_path = snapshot.save_snapshot(_assess_root_no_repo(tmp_path), tmp_path / "snap.json")

    rc, out, err = _run_diff(tmp_path, snap_path, capsys)
    assert rc == 0
    assert err == ""
    assert "| (no changes) | - | - |" in out


def test_cli_diff_snapshot_default_is_snapshot_json() -> None:
    """The --snapshot parser default is 'snapshot.json'."""
    parser = cli._build_parser()
    args = parser.parse_args(["diff", "--root", "/tmp/whatever"])
    assert args.snapshot == "snapshot.json"
    assert args.root == "/tmp/whatever"
