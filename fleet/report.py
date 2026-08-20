"""Markdown portfolio table renderer for fleet.

:func:`render_portfolio` turns a list of :class:`~fleet.health.ProjectHealth`
into a one-page markdown table sorted by last-activity descending (projects
with no activity sort last).

By default the table has six columns (Project, Last Cycle, Last Outcome, Days
Since Activity, Open Issues, Health). Passing a ``git_states`` mapping adds a
seventh ``Git`` column at the end summarizing each project's git-side work in
flight (an unmerged ``build*`` branch and/or unpushed commits); a clean
project renders ``-``.
"""

from __future__ import annotations

from fleet.gittest import EMPTY_STATE, GitState
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


def _fmt_git(gs: GitState) -> str:
    """Format a git work-in-flight summary for the ``Git`` column.

    A clean state (no unmerged ``build*`` branch and no unpushed commits)
    renders ``-``. Otherwise the parts are joined with ``,``:

    - ``unmerged:<b1>+<b2>`` — the unmerged ``build*`` branch names.
    - ``unpushed:<n>`` — the count of unpushed commits on ``main``.
    """
    if not gs.unmerged_build_branches and gs.unpushed_commits == 0:
        return "-"
    parts: list[str] = []
    if gs.unmerged_build_branches:
        parts.append("unmerged:" + "+".join(gs.unmerged_build_branches))
    if gs.unpushed_commits > 0:
        parts.append("unpushed:" + str(gs.unpushed_commits))
    return ",".join(parts)


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


def render_portfolio(
    healths: list[ProjectHealth],
    git_states: dict[str, GitState] | None = None,
) -> str:
    """Render a markdown portfolio status table.

    Parameters
    ----------
    healths:
        The per-project health rows to render.
    git_states:
        Optional mapping of project name -> :class:`~fleet.gittest.GitState`.
        When provided, a seventh ``Git`` column is appended at the end of each
        row summarizing that project's git-side work in flight (``-`` when
        clean, ``unmerged:<b1>+<b2>`` / ``unpushed:<n>`` otherwise). When
        ``None`` (the default) the output is the six-column table, byte-
        identical to the pre-git-column form.

    Returns
    -------
    str
        A markdown table (header + separator + one row per project), sorted by
        last-activity descending. An empty input yields a header-only table
        with a single "no projects" row.
    """
    rows = sorted(healths, key=_sort_key)
    with_git = git_states is not None

    header = "| Project | Last Cycle | Last Outcome | Days Since Activity | Open Issues | Health |"
    separator = "|---|---|---|---|---|---|"
    if with_git:
        header += " Git |"
        separator += "---|"
    lines = [header, separator]

    if not rows:
        no_projects = "| (no projects discovered) | - | - | - | - | - |"
        if with_git:
            no_projects += " - |"
        lines.append(no_projects)
        return "\n".join(lines)

    for h in rows:
        row = (
            f"| {h.name} | {_fmt_cycle(h.last_cycle)} | {_fmt_outcome(h.last_outcome)} "
            f"| {_fmt_days(h.days_since_activity)} | {h.open_issues} | {h.health} |"
        )
        if git_states is not None:
            row += f" {_fmt_git(git_states.get(h.name, EMPTY_STATE))} |"
        lines.append(row)
    return "\n".join(lines)
