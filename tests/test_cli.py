"""CLI `status` wiring test (preview for the CLI phase).

Confirms that `fleet.cli` `status` actually composes discover -> assess ->
render_portfolio and honors `--filter` (active/stalled/dead/all). The clock is
pinned (patch `health.datetime` with a `datetime` subclass whose `now()`
returns the fixed NOW, keeping `fromtimestamp` working) and the open-issue
lookup is patched so the output is deterministic.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from unittest import mock

from fleet import cli, health, report
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
