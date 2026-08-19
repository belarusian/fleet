"""Project AI-directory discovery for fleet.

A *project* is any directory under a scan root that contains an ``ai/``
subdirectory holding either a ``trajectories/`` subdirectory (with at least
one ``*.json``) or a gate log (``*gate*.md``). Discovery is pure and
deterministic: it walks the root in sorted order and returns a stable list.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Project:
    """One discovered project.

    Attributes
    ----------
    name:
        The project's directory name (the basename of the project dir).
    path:
        The project directory path (the dir that contains ``ai/``).
    ai_dir:
        The project's ``ai/`` directory path.
    """

    name: str
    path: Path
    ai_dir: Path


def _has_trajectories(ai: Path) -> bool:
    """True if *ai* has a ``trajectories/`` dir containing at least one JSON."""
    traj = ai / "trajectories"
    if not traj.is_dir():
        return False
    return any(traj.glob("*.json"))


def _has_gate_log(ai: Path) -> bool:
    """True if *ai* contains a gate log (``*gate*.md``)."""
    return any(ai.glob("*gate*.md"))


def is_project(ai: Path) -> bool:
    """Return True if *ai* is a project AI directory.

    A project AI directory is one that holds either trajectories or a gate
    log. This is the single predicate used by :func:`discover`.
    """
    if not ai.is_dir():
        return False
    return _has_trajectories(ai) or _has_gate_log(ai)


def discover(root: str | Path) -> list[Project]:
    """Discover every project AI directory under *root*.

    A project is any immediate-or-nested subdirectory ``<root>/.../ai`` that
    satisfies :func:`is_project`. To keep the portfolio table one page, the
    scan is bounded to depth 2 below *root* (``<root>/<project>/ai`` and
    ``<root>/<group>/<project>/ai``), which matches the four-pipeline layout.

    Parameters
    ----------
    root:
        The scan root (default ``~/AI`` is applied by the CLI, not here).

    Returns
    -------
    list[Project]
        Discovered projects, sorted by name. Empty when *root* is missing or
        holds no projects.
    """
    root_p = Path(root).expanduser()
    if not root_p.is_dir():
        return []

    found: list[Project] = []
    seen: set[Path] = set()

    # Depth 1: <root>/<project>/ai
    for child in sorted(root_p.iterdir()):
        if not child.is_dir():
            continue
        ai = child / "ai"
        if is_project(ai) and ai not in seen:
            seen.add(ai)
            found.append(Project(name=child.name, path=child, ai_dir=ai))

    # Depth 2: <root>/<group>/<project>/ai
    for group in sorted(root_p.iterdir()):
        if not group.is_dir():
            continue
        for child in sorted(group.iterdir()):
            if not child.is_dir():
                continue
            ai = child / "ai"
            if is_project(ai) and ai not in seen:
                seen.add(ai)
                found.append(Project(name=child.name, path=child, ai_dir=ai))

    found.sort(key=lambda p: p.name)
    return found
