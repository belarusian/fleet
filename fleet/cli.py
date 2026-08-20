"""The ``fleet`` command-line interface.

Subcommands:
  - ``fleet status [--root DIR] [--filter active|stalled|dead|stranded|paused|all]``
        Scan the root, assess each project, and print a markdown portfolio
        table (optionally filtered by health). The table always shows a
        ``Git`` column summarizing each project's git-side work in flight.
  - ``fleet snapshot [--root DIR] [--snapshot FILE]``
        Scan the root, assess each project, and save the portfolio as a JSON
        snapshot (the baseline that :func:`diff` compares against).
  - ``fleet diff [--root DIR] [--snapshot FILE]``
        Compare the current portfolio against a saved snapshot JSON and print
        a markdown diff table.

Design notes
------------
- ``--root`` defaults to ``~/AI`` on every subcommand.
- ``diff`` is deliberately *unfiltered*: it surfaces the full change set
  (added / removed / changed). A health filter does not map cleanly onto diff
  rows because ``removed`` rows have no resulting health, and filtering would
  hide part of the change set. Use ``status --filter`` for a health view of
  the current state.
- ``status --filter`` accepts the v1 classes (``active`` / ``stalled`` /
  ``dead``) and the two v2-only classes (``stranded`` / ``paused``). The v1
  classes match the ``health`` column (v1 classification); ``stranded`` and
  ``paused`` are selected with the v2 classifier
  (:func:`fleet.health.classify_health_v2`) over the project's git state.
  Full v2 integration of the ``health`` column is a later cycle.
- Machine-readable (``--json``) output is intentionally not provided yet: no
  consumer needs it, and the data model (``ProjectHealth`` / ``DiffRow``)
  would serialize trivially if a concrete consumer appears.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from fleet import __version__, discover, report
from fleet import health as health_mod
from fleet import snapshot as snapshot_mod
from fleet.gittest import EMPTY_STATE, GitState, read_gitstate
from fleet.health import classify_health_v2

_VALID_FILTERS = ("active", "stalled", "dead", "stranded", "paused", "all")


def _build_parser() -> argparse.ArgumentParser:
    """Build the top-level argument parser with the three subcommands."""
    parser = argparse.ArgumentParser(
        prog="fleet",
        description="Multi-project health scanner for the four pipeline.",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"fleet {__version__}",
        help="print the fleet version and exit",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    status = sub.add_parser("status", help="print the portfolio status table")
    status.add_argument(
        "--root",
        default="~/AI",
        help="scan root (default: ~/AI)",
    )
    status.add_argument(
        "--filter",
        dest="filter",
        default="all",
        choices=_VALID_FILTERS,
        help="filter rows by health (default: all)",
    )

    snap = sub.add_parser("snapshot", help="save the current portfolio as a snapshot JSON")
    snap.add_argument(
        "--root",
        default="~/AI",
        help="scan root (default: ~/AI)",
    )
    snap.add_argument(
        "--snapshot",
        default="snapshot.json",
        help="path to write the snapshot JSON (default: snapshot.json)",
    )

    diff = sub.add_parser("diff", help="diff the current portfolio against a snapshot")
    diff.add_argument(
        "--root",
        default="~/AI",
        help="scan root (default: ~/AI)",
    )
    diff.add_argument(
        "--snapshot",
        default="snapshot.json",
        help="path to the saved snapshot JSON (default: snapshot.json)",
    )
    return parser


def _assess_all(root: str) -> list[health_mod.ProjectHealth]:
    """Discover projects under *root* and assess each one.

    Note: the CLI passes no ``repo`` to :func:`fleet.health.assess`, so the
    ``open_issues`` column is always ``0`` in CLI output. The discovery layer
    has no project -> ``owner/repo`` mapping; programmatic callers can pass
    ``repo`` to :func:`fleet.health.assess` / :func:`fleet.health.project_health`
    to get real ``gh``-backed counts.
    """
    projects = discover.discover(root)
    return [health_mod.assess(p.name, p.ai_dir) for p in projects]


def _git_states(root: str) -> dict[str, GitState]:
    """Read the git work-in-flight state for every project under *root*.

    Returns a mapping of project name -> :class:`~fleet.gittest.GitState`.
    Projects that are not git repos (or have no ``main``) map to the empty
    state (a clean ``-`` in the ``Git`` column).
    """
    return {p.name: read_gitstate(p.path) for p in discover.discover(root)}


def _cmd_status(args: argparse.Namespace) -> int:
    """Run the ``status`` subcommand; return a process exit code."""
    healths = _assess_all(args.root)
    git_states = _git_states(args.root)
    if args.filter != "all":
        if args.filter in ("stranded", "paused"):
            healths = [
                h
                for h in healths
                if classify_health_v2(
                    h.days_since_activity,
                    h.last_outcome,
                    git_states.get(h.name, EMPTY_STATE),
                )
                == args.filter
            ]
        else:
            healths = [h for h in healths if h.health == args.filter]
    print(report.render_portfolio(healths, git_states))
    return 0


def _cmd_snapshot(args: argparse.Namespace) -> int:
    """Run the ``snapshot`` subcommand; return a process exit code."""
    healths = _assess_all(args.root)
    path = snapshot_mod.save_snapshot(healths, args.snapshot)
    print(f"saved {len(healths)} project(s) to {path}")
    return 0


def _cmd_diff(args: argparse.Namespace) -> int:
    """Run the ``diff`` subcommand; return a process exit code."""
    snap_path = Path(args.snapshot).expanduser()
    if not snap_path.is_file():
        print(f"error: snapshot not found: {snap_path}", file=sys.stderr)
        return 2
    snap = snapshot_mod.load_snapshot(snap_path)
    current = _assess_all(args.root)
    rows = snapshot_mod.snapshot_diff(snap, current)
    print(snapshot_mod.render_diff(rows))
    return 0


def main(argv: list[str] | None = None) -> int:
    """Entry point for the ``fleet`` console script."""
    parser = _build_parser()
    args = parser.parse_args(argv)
    if args.command == "status":
        return _cmd_status(args)
    if args.command == "snapshot":
        return _cmd_snapshot(args)
    if args.command == "diff":
        return _cmd_diff(args)
    parser.error(f"unknown command: {args.command}")
    return 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
