"""Snapshot save/load and diff for fleet.

A snapshot is a JSON document capturing the portfolio at one moment: a list of
per-project health rows plus a timestamp. :func:`snapshot_diff` compares a
current portfolio against a saved snapshot and reports what changed.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from fleet.health import ProjectHealth


@dataclass(frozen=True)
class Snapshot:
    """A saved portfolio snapshot.

    Attributes
    ----------
    created:
        The UTC timestamp the snapshot was taken.
    projects:
        The per-project health rows captured at that moment.
    """

    created: datetime
    projects: list[ProjectHealth] = field(default_factory=list)


def _health_to_dict(h: ProjectHealth) -> dict:
    """Serialize one :class:`ProjectHealth` to a JSON-safe dict."""
    return {
        "name": h.name,
        "last_cycle": h.last_cycle,
        "last_outcome": h.last_outcome,
        "days_since_activity": h.days_since_activity,
        "open_issues": h.open_issues,
        "health": h.health,
        "last_activity": h.last_activity.isoformat() if h.last_activity else None,
    }


def _health_from_dict(d: dict) -> ProjectHealth:
    """Rebuild a :class:`ProjectHealth` from a JSON-safe dict."""
    last_activity = d.get("last_activity")
    if isinstance(last_activity, str):
        last_activity = datetime.fromisoformat(last_activity)
    else:
        last_activity = None
    return ProjectHealth(
        name=d["name"],
        last_cycle=d.get("last_cycle"),
        last_outcome=d.get("last_outcome"),
        days_since_activity=d.get("days_since_activity"),
        open_issues=d.get("open_issues", 0),
        health=d.get("health", "dead"),
        last_activity=last_activity,
    )


def save_snapshot(healths: list[ProjectHealth], path: str | Path) -> Path:
    """Save *healths* as a JSON snapshot at *path*.

    Returns the path written.
    """
    p = Path(path).expanduser()
    p.parent.mkdir(parents=True, exist_ok=True)
    doc = {
        "created": datetime.now(tz=timezone.utc).isoformat(),
        "projects": [_health_to_dict(h) for h in healths],
    }
    p.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")
    return p


def load_snapshot(path: str | Path) -> Snapshot:
    """Load a snapshot from the JSON file at *path*.

    Raises ``FileNotFoundError`` if the file is missing and ``ValueError`` if
    the document is malformed.
    """
    p = Path(path).expanduser()
    if not p.is_file():
        raise FileNotFoundError(f"snapshot not found: {p}")
    doc = json.loads(p.read_text(encoding="utf-8"))
    if not isinstance(doc, dict) or "projects" not in doc:
        raise ValueError(f"malformed snapshot: {p}")
    created_raw = doc.get("created")
    created = (
        datetime.fromisoformat(created_raw)
        if isinstance(created_raw, str)
        else datetime.now(tz=timezone.utc)
    )
    projects = [_health_from_dict(d) for d in doc["projects"] if isinstance(d, dict)]
    return Snapshot(created=created, projects=projects)


@dataclass(frozen=True)
class DiffRow:
    """One project's change between a snapshot and the current portfolio.

    Attributes
    ----------
    name:
        The project name.
    status:
        ``"added"`` (new since snapshot), ``"removed"`` (gone), or
        ``"changed"`` / ``"unchanged"``.
    detail:
        A short human-readable description of the change (empty when
        unchanged).
    """

    name: str
    status: str
    detail: str = ""


def snapshot_diff(snapshot: Snapshot, current: list[ProjectHealth]) -> list[DiffRow]:
    """Compare *current* against *snapshot* and report per-project changes.

    A project is ``added`` when it is in *current* but not the snapshot,
    ``removed`` when it is in the snapshot but not *current*, ``changed`` when
    any tracked field differs, and ``unchanged`` otherwise. Rows are sorted by
    name.
    """
    snap_by_name = {h.name: h for h in snapshot.projects}
    cur_by_name = {h.name: h for h in current}
    rows: list[DiffRow] = []

    for name in sorted(set(snap_by_name) | set(cur_by_name)):
        in_snap = name in snap_by_name
        in_cur = name in cur_by_name
        if in_cur and not in_snap:
            rows.append(DiffRow(name=name, status="added", detail="new project"))
        elif in_snap and not in_cur:
            rows.append(DiffRow(name=name, status="removed", detail="no longer discovered"))
        else:
            s = snap_by_name[name]
            c = cur_by_name[name]
            changes = _field_changes(s, c)
            if changes:
                rows.append(DiffRow(name=name, status="changed", detail=", ".join(changes)))
            else:
                rows.append(DiffRow(name=name, status="unchanged"))
    return rows


def _field_changes(s: ProjectHealth, c: ProjectHealth) -> list[str]:
    """List the human-readable field changes between two health rows."""
    changes: list[str] = []
    if s.last_cycle != c.last_cycle:
        changes.append(f"cycle {s.last_cycle}->{c.last_cycle}")
    if s.last_outcome != c.last_outcome:
        changes.append(f"outcome {s.last_outcome}->{c.last_outcome}")
    if s.health != c.health:
        changes.append(f"health {s.health}->{c.health}")
    if s.open_issues != c.open_issues:
        changes.append(f"issues {s.open_issues}->{c.open_issues}")
    return changes


def render_diff(rows: list[DiffRow]) -> str:
    """Render a diff as a markdown table (only changed/added/removed rows)."""
    lines = [
        "| Project | Status | Detail |",
        "|---|---|---|",
    ]
    shown = [r for r in rows if r.status != "unchanged"]
    if not shown:
        lines.append("| (no changes) | - | - |")
        return "\n".join(lines)
    for r in shown:
        lines.append(f"| {r.name} | {r.status} | {r.detail or '-'} |")
    return "\n".join(lines)
