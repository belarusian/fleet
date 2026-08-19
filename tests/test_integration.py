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


def _build_mixed_root(root: Path) -> None:
    """Build a mixed root: a healthy project, a corrupt-JSON project, and a gate-only project.

    - ``healthy``  — 3 trajectories, active (1 day).
    - ``corrupt``  — one corrupt + one good trajectory, active (1 day).
    - ``gateonly`` — a gate log with a red-gate cycle block, no trajectories (dead).
    """
    make_project(root, "healthy", now=NOW, days_ago=1, n_traj=3, outcome="exit:task_complete")

    # corrupt: a corrupt JSON plus a good one; only the good one parses.
    corrupt_ai = make_project(
        root, "corrupt", now=NOW, days_ago=1, n_traj=1, outcome="max_steps_reached"
    )
    (corrupt_ai / "trajectories" / "bad.json").write_text("{not valid json", encoding="utf-8")

    # gateonly: a gate log with a red-gate cycle block, no trajectories.
    gateonly_ai = root / "gateonly" / "ai"
    gateonly_ai.mkdir(parents=True)
    gateonly_ai.joinpath("cycle-001-gate.md").write_text(
        "## Build Order\n\n"
        "| Phase | Cycles | Target |\n"
        "|---|---|---|\n"
        "| Foundations | 1 | core |\n\n"
        "## Cycle 1: Pending\n\n"
        "### Results\n\n"
        "| Check | Before | After |\n"
        "|---|---|---|\n"
        "| Gate (build+test+lint) | red | red |\n"
        "| Merged on main | — | — |\n",
        encoding="utf-8",
    )
    import os

    os.utime(gateonly_ai / "cycle-001-gate.md", (NOW.timestamp(), NOW.timestamp()))


def test_integration_mixed_root_pipeline(tmp_path: Path) -> None:
    """A mixed root (healthy + corrupt-JSON + gate-only) flows through discover->assess->render.

    The corrupt-JSON project is still discovered and assessed (its good file
    parses); the gate-only project is discovered, assessed as dead, and its
    outcome is derived from the gate log. The full table renders without error.
    """
    _build_mixed_root(tmp_path)
    projects = discover.discover(tmp_path)
    assert sorted(p.name for p in projects) == ["corrupt", "gateonly", "healthy"]

    with mock.patch.object(health, "count_open_issues", side_effect=_issues):
        assessed = [
            health.assess(p.name, p.ai_dir, repo=f"owner/{p.name}", now=NOW) for p in projects
        ]
    by_name = {h.name: h for h in assessed}

    # healthy: 3 trajectories, active, its outcome.
    assert by_name["healthy"].health == "active"
    assert by_name["healthy"].last_cycle == 3
    assert by_name["healthy"].last_outcome == "exit:task_complete"

    # corrupt: only the good file parses -> 1 trajectory, active, its outcome.
    assert by_name["corrupt"].health == "active"
    assert by_name["corrupt"].last_cycle == 1
    assert by_name["corrupt"].last_outcome == "max_steps_reached"

    # gateonly: no trajectories -> dead; outcome derived from the red gate block.
    assert by_name["gateonly"].health == "dead"
    assert by_name["gateonly"].last_cycle == 1
    assert by_name["gateonly"].last_outcome == "gate:red"

    # The full table renders all three rows without error.
    md = report.render_portfolio(assessed)
    names = [ln.split("|")[1].strip() for ln in md.splitlines()[2:]]
    assert sorted(names) == ["corrupt", "gateonly", "healthy"]
