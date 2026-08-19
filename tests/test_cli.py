"""CLI `status` wiring test (preview for the CLI phase).

Confirms that `fleet.cli` `status` actually composes discover -> assess ->
render_portfolio and honors `--filter` (active/stalled/dead/all). The clock is
pinned (patch `health.datetime` with a `datetime` subclass whose `now()`
returns the fixed NOW, keeping `fromtimestamp` working) and the open-issue
lookup is patched so the output is deterministic.
"""

from __future__ import annotations

import argparse
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock

import pytest

from fleet import __version__, cli, health, report, snapshot
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


# ---------------------------------------------------------------------------
# CLI `snapshot` subcommand
# ---------------------------------------------------------------------------


def _run_snapshot(root: Path, snap_path: Path, capsys) -> tuple[int, str, str]:
    """Run ``fleet snapshot --root <root> --snapshot <snap>``; return (rc, out, err)."""
    argv = ["snapshot", "--root", str(root), "--snapshot", str(snap_path)]
    with mock.patch.object(health, "count_open_issues", side_effect=_issues), mock.patch.object(
        health, "datetime", _FakeDatetime
    ):
        rc = cli.main(argv)
    out, err = capsys.readouterr()
    return rc, out, err


def test_cli_snapshot_saves_current_portfolio(tmp_path: Path, capsys) -> None:
    """`snapshot` writes the assessed portfolio to the target path and exits 0."""
    _build_root(tmp_path)
    snap_path = tmp_path / "snap.json"
    rc, out, err = _run_snapshot(tmp_path, snap_path, capsys)

    assert rc == 0
    assert err == ""
    assert snap_path.is_file()
    # The saved snapshot round-trips to the assessed portfolio (no repo).
    snap = snapshot.load_snapshot(snap_path)
    assessed = _assess_root_no_repo(tmp_path)
    assert [h.name for h in snap.projects] == [h.name for h in assessed]
    for saved, cur in zip(snap.projects, assessed, strict=True):
        assert saved.name == cur.name
        assert saved.health == cur.health
        assert saved.last_cycle == cur.last_cycle
        assert saved.last_outcome == cur.last_outcome
    # stdout reports the count and the path written.
    assert "3 project(s)" in out
    assert str(snap_path) in out


def test_cli_snapshot_creates_parent_dirs(tmp_path: Path, capsys) -> None:
    """`snapshot` creates missing parent directories for the target path."""
    _build_root(tmp_path)
    nested = tmp_path / "deep" / "nested" / "snap.json"
    rc, out, err = _run_snapshot(tmp_path, nested, capsys)
    assert rc == 0
    assert nested.is_file()
    assert snapshot.load_snapshot(nested).projects


def test_cli_snapshot_then_diff_is_end_to_end(tmp_path: Path, capsys) -> None:
    """A `snapshot` baseline followed by an unchanged `diff` reports no changes."""
    _build_root(tmp_path)
    snap_path = tmp_path / "snap.json"
    rc1, _, _ = _run_snapshot(tmp_path, snap_path, capsys)
    assert rc1 == 0

    # Portfolio is unchanged, so diff against the just-saved baseline is empty.
    rc2, out, err = _run_diff(tmp_path, snap_path, capsys)
    assert rc2 == 0
    assert err == ""
    assert "| (no changes) | - | - |" in out


def test_cli_snapshot_then_diff_shows_changes(tmp_path: Path, capsys) -> None:
    """A `snapshot` baseline followed by a mutated `diff` surfaces the change."""
    _build_root(tmp_path)
    snap_path = tmp_path / "snap.json"
    rc1, _, _ = _run_snapshot(tmp_path, snap_path, capsys)
    assert rc1 == 0

    # Add a new project after the baseline; diff must surface it as `added`.
    make_project(tmp_path, "delta", now=NOW, days_ago=2, n_traj=2, outcome="exit:task_complete")
    rc2, out, err = _run_diff(tmp_path, snap_path, capsys)
    assert rc2 == 0
    assert err == ""
    assert "| delta | added |" in out


# ---------------------------------------------------------------------------
# --root default (pins the documented ~/AI default on every subcommand)
# ---------------------------------------------------------------------------


def test_cli_root_defaults_to_home_ai() -> None:
    """Every subcommand's --root defaults to '~/AI'."""
    parser = cli._build_parser()
    for cmd in ("status", "snapshot", "diff"):
        args = parser.parse_args([cmd])
        assert args.root == "~/AI", f"{cmd}: --root default should be ~/AI"


def test_cli_snapshot_default_is_snapshot_json() -> None:
    """The snapshot subcommand's --snapshot default is 'snapshot.json'."""
    parser = cli._build_parser()
    args = parser.parse_args(["snapshot", "--root", "/tmp/whatever"])
    assert args.snapshot == "snapshot.json"
    assert args.root == "/tmp/whatever"


# ---------------------------------------------------------------------------
# TICKET-028: open_issues is always 0 in CLI output (no repo mapping)
# ---------------------------------------------------------------------------


def test_cli_open_issues_always_zero(tmp_path: Path, capsys) -> None:
    """CLI output always shows 0 open issues because no repo is passed.

    The CLI's _assess_all calls assess(name, ai_dir) without a repo argument.
    assess defaults repo=None, and count_open_issues(None) returns 0 via its
    guard clause (health.py: if not repo: return 0). This test verifies the
    end-to-end behavior: the Open Issues column is 0 for every row.
    """
    _build_root(tmp_path)
    # Do NOT patch count_open_issues — it will be called with None and return 0
    # via the guard clause without invoking subprocess.
    with mock.patch.object(health, "datetime", _FakeDatetime):
        rc = cli.main(["status", "--root", str(tmp_path)])
    assert rc == 0
    out = capsys.readouterr().out
    # Each data row has the form: | name | cycle | outcome | days | 0 | health |
    # Verify the open-issues column (5th) is 0 in every data row.
    lines = out.strip().splitlines()
    data_rows = [
        ln for ln in lines if ln.startswith("|") and "---" not in ln and "Project" not in ln
    ]
    assert len(data_rows) == 3  # alpha, beta, gamma
    for row in data_rows:
        cols = [c.strip() for c in row.split("|") if c.strip()]
        # cols: [name, cycle, outcome, days, open_issues, health]
        assert cols[4] == "0", f"Expected open_issues=0 in row: {row}"


# ---------------------------------------------------------------------------
# CLI surface guard (TICKET-042): pins the registered subcommands and that
# each subcommand's --help works. Catches a removed/renamed subcommand.
# ---------------------------------------------------------------------------


def _run_help(argv: list[str], capsys) -> str:
    """Run ``cli.main(argv)`` expecting argparse ``--help`` (SystemExit 0).

    Returns the captured stdout. ``--help`` short-circuits before any command
    runs, so no root/~/AI is touched and no mocking is needed.
    """
    with pytest.raises(SystemExit) as exc:
        cli.main(argv)
    assert exc.value.code == 0
    return capsys.readouterr().out


def test_cli_top_level_help_lists_all_subcommands(capsys) -> None:
    """``fleet --help`` lists all three subcommands: status, snapshot, diff."""
    out = _run_help(["--help"], capsys)
    for name in ("status", "snapshot", "diff"):
        assert name in out


def test_cli_registered_subcommands_are_exactly_three() -> None:
    """The parser registers exactly {status, snapshot, diff} — no more, no less."""
    parser = cli._build_parser()
    sub = next(
        a for a in parser._actions if isinstance(a, argparse._SubParsersAction)
    )
    assert set(sub.choices) == {"status", "snapshot", "diff"}


def test_cli_status_help_shows_filter(capsys) -> None:
    """``status --help`` exits 0 and shows the --filter option."""
    out = _run_help(["status", "--help"], capsys)
    assert "--filter" in out


def test_cli_snapshot_help_shows_snapshot(capsys) -> None:
    """``snapshot --help`` exits 0 and shows the --snapshot option."""
    out = _run_help(["snapshot", "--help"], capsys)
    assert "--snapshot" in out


def test_cli_diff_help_shows_snapshot(capsys) -> None:
    """``diff --help`` exits 0 and shows the --snapshot option."""
    out = _run_help(["diff", "--help"], capsys)
    assert "--snapshot" in out


# ---------------------------------------------------------------------------
# Release: top-level --version flag (TICKET-048)
# ---------------------------------------------------------------------------


def test_cli_version_flag_exits_zero_and_prints_version(capsys) -> None:
    """``fleet --version`` exits 0 and prints a line containing the version.

    argparse's ``action="version"`` writes to stdout and raises
    ``SystemExit(0)``. The printed line must contain ``fleet.__version__``.
    """
    with pytest.raises(SystemExit) as exc:
        cli.main(["--version"])
    assert exc.value.code == 0
    out = capsys.readouterr().out
    assert __version__ in out


def test_cli_version_flag_prints_exact_version(capsys) -> None:
    """The ``--version`` output is exactly ``fleet <__version__>``.

    Pins the version string so a silent bump in ``fleet/__init__.py`` is
    caught here (and in ``pyproject.toml`` via the packaging metadata).
    """
    with pytest.raises(SystemExit) as exc:
        cli.main(["--version"])
    assert exc.value.code == 0
    out = capsys.readouterr().out
    assert out.strip() == f"fleet {__version__}"


def test_cli_version_is_0_1_0() -> None:
    """The shipped version is pinned to 0.1.0 (first release)."""
    assert __version__ == "0.1.0"


# ---------------------------------------------------------------------------
# TICKET-051: `python3 -m fleet` works via fleet/__main__.py
# ---------------------------------------------------------------------------


def test_python_m_fleet_help_exits_zero(tmp_path: Path) -> None:
    """``python3 -m fleet --help`` exits 0 from a neutral directory.

    Runs the package as a script module from a tmp_path (not the repo root)
    with PYTHONPATH pointing at the repo root, so the test exercises real
    package resolution rather than the ambient cwd. Asserts returncode == 0
    and that the help text mentions the ``status`` subcommand.
    """
    import os
    import subprocess
    import sys

    repo_root = Path(__file__).resolve().parent.parent
    env = dict(os.environ)
    # Prepend the repo root so `fleet` is importable from a neutral cwd.
    existing = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = str(repo_root) + (os.pathsep + existing if existing else "")

    result = subprocess.run(
        [sys.executable, "-m", "fleet", "--help"],
        cwd=str(tmp_path),
        env=env,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, f"stderr: {result.stderr}"
    assert "status" in result.stdout


def test_python_m_fleet_version_exits_zero_and_prints_version(tmp_path: Path) -> None:
    """``python3 -m fleet --version`` exits 0 and prints the version.

    Exercises the ``sys.exit(main())`` path in ``fleet/__main__.py`` with
    argparse's ``action="version"`` (which raises ``SystemExit(0)`` rather
    than returning), from a neutral tmp_path with PYTHONPATH set to the repo
    root. Asserts returncode == 0 and that stdout is exactly
    ``fleet <__version__>``.
    """
    import os
    import subprocess
    import sys

    repo_root = Path(__file__).resolve().parent.parent
    env = dict(os.environ)
    existing = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = str(repo_root) + (os.pathsep + existing if existing else "")

    result = subprocess.run(
        [sys.executable, "-m", "fleet", "--version"],
        cwd=str(tmp_path),
        env=env,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, f"stderr: {result.stderr}"
    assert result.stdout.strip() == f"fleet {__version__}"
