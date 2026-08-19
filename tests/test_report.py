"""Tests for fleet.report (markdown portfolio table renderer).

Covers :func:`fleet.report.render_portfolio`: empty input, mixed-health
ordering, the no-activity-last tie-break, and a full multi-project table
where ``None`` fields render as ``-``.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fleet.health import ProjectHealth
from fleet.report import render_portfolio

NOW = datetime(2025, 6, 1, 12, 0, 0, tzinfo=timezone.utc)


def _ph(
    name: str,
    health: str,
    *,
    last_activity: datetime | None = None,
    last_cycle: int | None = None,
    last_outcome: str | None = None,
    days: int | None = None,
    open_issues: int = 0,
) -> ProjectHealth:
    """Build a :class:`ProjectHealth` row with sensible defaults for table tests."""
    return ProjectHealth(
        name=name,
        last_cycle=last_cycle,
        last_outcome=last_outcome,
        days_since_activity=days,
        open_issues=open_issues,
        health=health,
        last_activity=last_activity,
    )


def _names(md: str) -> list[str]:
    """Extract the project name (first column) from each data row of *md*."""
    lines = md.splitlines()
    # lines[0] = header, lines[1] = separator; the rest are data rows.
    return [ln.split("|")[1].strip() for ln in lines[2:]]


def test_render_portfolio_empty_input() -> None:
    """An empty input yields a header-only table with a single no-projects row."""
    md = render_portfolio([])
    lines = md.splitlines()
    assert lines[0] == (
        "| Project | Last Cycle | Last Outcome | Days Since Activity | Open Issues | Health |"
    )
    assert lines[1] == "|---|---|---|---|---|---|"
    assert lines[2] == "| (no projects discovered) | - | - | - | - | - |"
    assert len(lines) == 3


def test_render_portfolio_mixed_health_ordering() -> None:
    """Rows are sorted by last-activity descending (most recent first)."""
    healths = [
        _ph("old", "dead", last_activity=NOW, days=31),
        _ph("new", "active", last_activity=NOW, days=1),
        _ph("mid", "stalled", last_activity=NOW, days=20),
    ]
    # Shuffle the input order so the sort (not insertion order) is what's tested.
    shuffled = [healths[2], healths[0], healths[1]]
    md = render_portfolio(shuffled)
    # All three share the same last_activity, so the health tie-break applies:
    # active (new) -> stalled (mid) -> dead (old).
    assert _names(md) == ["new", "mid", "old"]


def test_render_portfolio_no_activity_last() -> None:
    """Projects with no activity (last_activity is None) sort after all active ones."""
    healths = [
        _ph("noact", "dead", last_activity=None, days=None),
        _ph("recent", "active", last_activity=NOW, days=1),
        _ph("older", "stalled", last_activity=NOW, days=20),
    ]
    md = render_portfolio(healths)
    names = _names(md)
    # The no-activity project must be last, regardless of its (dead) health.
    assert names[-1] == "noact"
    # The two with activity come first, most-recent first (same ts -> health tie-break).
    assert names[:2] == ["recent", "older"]


def test_render_portfolio_full_table_none_fields() -> None:
    """A multi-project table renders None fields as '-' and preserves row order."""
    healths = [
        _ph("alpha", "active", last_activity=NOW, last_cycle=5, last_outcome="exit:task_complete",
            days=1, open_issues=3),
        _ph("beta", "stalled", last_activity=NOW, last_cycle=None, last_outcome=None,
            days=20, open_issues=0),
        _ph("gamma", "dead", last_activity=None, last_cycle=None, last_outcome=None,
            days=None, open_issues=0),
    ]
    md = render_portfolio(healths)
    lines = md.splitlines()
    assert lines[0] == (
        "| Project | Last Cycle | Last Outcome | Days Since Activity | Open Issues | Health |"
    )
    assert lines[1] == "|---|---|---|---|---|---|"
    # alpha (active) first, beta (stalled) second, gamma (no activity) last.
    assert lines[2] == "| alpha | 5 | exit:task_complete | 1 | 3 | active |"
    # beta: None cycle/outcome render as '-'.
    assert lines[3] == "| beta | - | - | 20 | 0 | stalled |"
    # gamma: None cycle/outcome/days render as '-'.
    assert lines[4] == "| gamma | - | - | - | 0 | dead |"
    assert len(lines) == 5


def test_render_portfolio_last_activity_descending() -> None:
    """The primary sort key is last-activity descending, dominating health.

    A `dead` project active 1 day ago must render ABOVE an `active` project
    idle 20 days: the time key (first in _sort_key) beats the health key
    (third), so recency — not health — orders the rows.
    """
    recent_dead = _ph(
        "recent_dead",
        "dead",
        last_activity=NOW - timedelta(days=1),
        days=1,
    )
    old_active = _ph(
        "old_active",
        "active",
        last_activity=NOW - timedelta(days=20),
        days=20,
    )
    md = render_portfolio([old_active, recent_dead])
    assert _names(md) == ["recent_dead", "old_active"]
