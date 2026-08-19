"""End-to-end integration test: discover -> assess -> render_portfolio.

Ties the Classification half (fleet.health) and the Report half
(fleet.report) together through the real discovery seam: build a
multi-project root, discover it, assess every project with a pinned clock,
and render the portfolio. The full pipeline must yield a correctly-sorted
(last-activity descending) and correctly-formatted markdown table.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from unittest import mock

from fleet import discover, health, report
from tests._fixtures import make_project

NOW = datetime(2025, 6, 1, 12, 0, 0, tzinfo=timezone.utc)


def _issues(repo: str | None) -> int:
    """Deterministic open-issue counts keyed by the owner/repo string."""
    return {"owner/alpha": 3, "owner/beta": 1, "owner/gamma": 0}.get(repo or "", 0)


def _build_root(root: Path) -> None:
    """Create three projects in distinct health states with distinct recency.

    days_ago 1/20/40 -> active/stalled/dead, and the distinct last-activity
    timestamps (NOW-1d, NOW-20d, NOW-40d) exercise the primary sort key.
    """
    make_project(root, "alpha", now=NOW, days_ago=1, n_traj=3, outcome="exit:task_complete")
    make_project(root, "beta", now=NOW, days_ago=20, n_traj=2, outcome="max_steps_reached")
    make_project(root, "gamma", now=NOW, days_ago=40, n_traj=1, outcome="timeout")


def _assess_root(root: Path) -> list[health.ProjectHealth]:
    """Run the real discover -> assess seam over *root* with a pinned clock."""
    projects = discover.discover(root)
    with mock.patch.object(health, "count_open_issues", side_effect=_issues):
        return [
            health.assess(p.name, p.ai_dir, repo=f"owner/{p.name}", now=NOW) for p in projects
        ]


def test_integration_pipeline_sorted_and_formatted(tmp_path: Path) -> None:
    """The full pipeline yields a last-activity-desc, correctly-formatted table."""
    _build_root(tmp_path)
    assessed = _assess_root(tmp_path)

    # The Classification half: each project lands in a distinct health state.
    by_name = {h.name: h for h in assessed}
    assert by_name["alpha"].health == "active"
    assert by_name["beta"].health == "stalled"
    assert by_name["gamma"].health == "dead"

    # The Report half: the full table is sorted last-activity desc and formatted.
    md = report.render_portfolio(assessed)
    assert md == (
        "| Project | Last Cycle | Last Outcome | Days Since Activity | Open Issues | Health |\n"
        "|---|---|---|---|---|---|\n"
        "| alpha | 3 | exit:task_complete | 1 | 3 | active |\n"
        "| beta | 2 | max_steps_reached | 20 | 1 | stalled |\n"
        "| gamma | 1 | timeout | 40 | 0 | dead |"
    )


def test_integration_discover_feeds_assess(tmp_path: Path) -> None:
    """Every discovered project is assessed and appears exactly once in the table."""
    _build_root(tmp_path)
    assessed = _assess_root(tmp_path)

    discovered = [p.name for p in discover.discover(tmp_path)]
    assert sorted(discovered) == ["alpha", "beta", "gamma"]
    assert sorted(h.name for h in assessed) == ["alpha", "beta", "gamma"]

    md = report.render_portfolio(assessed)
    names = [ln.split("|")[1].strip() for ln in md.splitlines()[2:]]
    # Most-recent first: alpha (1d), beta (20d), gamma (40d).
    assert names == ["alpha", "beta", "gamma"]
