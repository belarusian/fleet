"""Markdown portfolio table renderer for fleet.

:func:`render_portfolio` turns a list of :class:`~fleet.health.ProjectHealth`
into a one-page markdown table sorted by last-activity descending (projects
with no activity sort last).
"""

from __future__ import annotations

from fleet.health import ProjectHealth

# Health labels in display order (most to least healthy).
_HEALTH_ORDER = {"active": 0, "stalled": 1, "dead": 2}


def _fmt_days(days: int | None) -> str:
    """Format a days-since-activity value for the table (``-`` when unknown)."""
    return "-" if days is None else str(days)


def _fmt_cycle(cycle: int | None) -> str:
    """Format a last-cycle value for the table (``-`` when unknown)."""
    return "-" if cycle is None else str(cycle)


def _fmt_outcome(outcome: str | None) -> str:
    """Format a last-outcome value for the table (``-`` when unknown)."""
    return "-" if outcome is None else outcome


def _sort_key(h: ProjectHealth) -> tuple[int, float, int, str]:
    """Sort key: last-activity descending, then health, then name.

    Projects with no activity (``last_activity is None``) sort last. Ties are
    broken by health (active first) then name for a stable, readable table.
    """
    if h.last_activity is None:
        time_key = 1
        ts = 0.0
    else:
        time_key = 0
        ts = h.last_activity.timestamp()
    return (time_key, -ts, _HEALTH_ORDER.get(h.health, 3), h.name)


def render_portfolio(healths: list[ProjectHealth]) -> str:
    """Render a markdown portfolio status table.

    Parameters
    ----------
    healths:
        The per-project health rows to render.

    Returns
    -------
    str
        A markdown table (header + separator + one row per project), sorted by
        last-activity descending. An empty input yields a header-only table
        with a single "no projects" row.
    """
    rows = sorted(healths, key=_sort_key)

    lines = [
        "| Project | Last Cycle | Last Outcome | Days Since Activity | Open Issues | Health |",
        "|---|---|---|---|---|---|",
    ]
    if not rows:
        lines.append("| (no projects discovered) | - | - | - | - | - |")
        return "\n".join(lines)

    for h in rows:
        lines.append(
            f"| {h.name} | {_fmt_cycle(h.last_cycle)} | {_fmt_outcome(h.last_outcome)} "
            f"| {_fmt_days(h.days_since_activity)} | {h.open_issues} | {h.health} |"
        )
    return "\n".join(lines)
