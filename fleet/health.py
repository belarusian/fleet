"""Per-project health metrics and classification for fleet.

For each discovered project, :func:`assess` uses the ``fourseer`` parsers to
extract the last cycle number, the last outcome, days since last activity, the
open issue count, and a health classification.

Health classification (by days since last activity):
  - ``active``  — ran within 7 days
  - ``stalled`` — 8-30 days
  - ``dead``    — 30+ days, or no trajectories at all
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import fourseer

# Day thresholds for the health classification.
ACTIVE_MAX_DAYS = 7
STALLED_MAX_DAYS = 30

# Files under an ai/ dir that count as "activity" for the recency signal.
_ACTIVITY_GLOBS = ("trajectories/*.json", "cycles*.out", "*gate*.md")


@dataclass(frozen=True)
class ProjectHealth:
    """Health metrics for one project.

    Attributes
    ----------
    name:
        The project name.
    last_cycle:
        The last cycle number, or ``None`` when no cycle is recorded.
    last_outcome:
        The last recorded outcome string, or ``None``.
    days_since_activity:
        Whole days since the most recent activity, or ``None`` when there is no
        activity signal at all.
    open_issues:
        The open issue count (from ``gh`` when available, else ``0``).
    health:
        One of ``"active"`` / ``"stalled"`` / ``"dead"``.
    last_activity:
        The most recent activity timestamp (UTC), or ``None``.
    """

    name: str
    last_cycle: int | None
    last_outcome: str | None
    days_since_activity: int | None
    open_issues: int
    health: str
    last_activity: datetime | None


def _last_activity(ai_dir: Path) -> datetime | None:
    """Return the most recent mtime (UTC) among activity files under *ai_dir*.

    Returns ``None`` when no activity file exists.
    """
    latest: float | None = None
    for pattern in _ACTIVITY_GLOBS:
        for f in ai_dir.glob(pattern):
            if f.is_file():
                mtime = f.stat().st_mtime
                if latest is None or mtime > latest:
                    latest = mtime
    if latest is None:
        return None
    return datetime.fromtimestamp(latest, tz=timezone.utc)


def _last_cycle_and_outcome(ai_dir: Path) -> tuple[int | None, str | None]:
    """Extract the last cycle number and last outcome for *ai_dir*.

    The last cycle number is the maximum cycle number seen in ``cycles.out``
    or the gate log; when neither records a cycle it falls back to the number
    of trajectories. The last outcome is the outcome of the highest-numbered
    cycle (from ``cycles.out``), else the last trajectory's outcome.
    """
    run = fourseer.load_run(ai_dir)

    cycle_nos = [c.cycle_no for c in run.cycles]
    gate_nos = [b.cycle_no for b in run.gate_log.cycles]
    last_cycle: int | None = None
    if cycle_nos or gate_nos:
        last_cycle = max(cycle_nos + gate_nos)
    elif run.trajectories:
        last_cycle = len(run.trajectories)

    last_outcome: str | None = None
    if run.cycles:
        top = max(run.cycles, key=lambda c: c.cycle_no)
        last_outcome = top.outcome
    if last_outcome is None and run.trajectories:
        # Trajectories load in sorted filename order; the last is the newest.
        last_outcome = run.trajectories[-1].outcome

    return last_cycle, last_outcome


def count_open_issues(repo: str | None) -> int:
    """Return the open issue count for *repo* via ``gh``, or ``0`` if unavailable.

    ``gh`` is best-effort: any failure (missing binary, no auth, no network,
    bad repo) yields ``0`` rather than raising, so a portfolio scan never
    aborts on one project's issue lookup.
    """
    if not repo:
        return 0
    try:
        proc = subprocess.run(
            ["gh", "issue", "list", "--repo", repo, "--state", "open", "--limit", "1000"],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return 0
    if proc.returncode != 0:
        return 0
    lines = [ln for ln in proc.stdout.splitlines() if ln.strip()]
    return len(lines)


def classify_health(days: int | None, has_trajectories: bool) -> str:
    """Classify health from days-since-activity and trajectory presence.

    ``dead`` when there are no trajectories or the project is 30+ days idle;
    ``stalled`` at 8-30 days; ``active`` within 7 days. A ``None`` day count
    (no activity signal) is treated as ``dead`` unless trajectories exist, in
    which case it is ``stalled`` (present but not recently active).
    """
    if not has_trajectories:
        return "dead"
    if days is None:
        return "stalled"
    if days <= ACTIVE_MAX_DAYS:
        return "active"
    if days <= STALLED_MAX_DAYS:
        return "stalled"
    return "dead"


def _days_between(now: datetime, then: datetime) -> int:
    """Whole days between *then* and *now* (floor of the day difference)."""
    delta = now - then
    return max(0, delta.days)


def assess(
    name: str,
    ai_dir: str | Path,
    repo: str | None = None,
    *,
    now: datetime | None = None,
) -> ProjectHealth:
    """Assess the health of one project.

    Parameters
    ----------
    name:
        The project name.
    ai_dir:
        The project's ``ai/`` directory.
    repo:
        Optional GitHub ``owner/repo`` for the open-issue lookup.
    now:
        Optional reference "now" (UTC) for deterministic tests. Defaults to
        the current UTC time.
    """
    ai = Path(ai_dir).expanduser()
    now = now or datetime.now(tz=timezone.utc)

    run = fourseer.load_run(ai)
    has_traj = len(run.trajectories) > 0

    last_cycle, last_outcome = _last_cycle_and_outcome(ai)
    last_activity = _last_activity(ai)
    days = _days_between(now, last_activity) if last_activity is not None else None
    health = classify_health(days, has_traj)
    open_issues = count_open_issues(repo)

    return ProjectHealth(
        name=name,
        last_cycle=last_cycle,
        last_outcome=last_outcome,
        days_since_activity=days,
        open_issues=open_issues,
        health=health,
        last_activity=last_activity,
    )
