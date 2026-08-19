"""The ``fleet`` command-line interface.

Subcommands:
  - ``fleet status [--root DIR] [--filter active|stalled|dead|all]``
        Scan the root, assess each project, and print a markdown portfolio
        table (optionally filtered by health).
  - ``fleet diff [--root DIR] [--snapshot FILE]``
        Compare the current portfolio against a saved snapshot JSON and print
        a markdown diff table.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from fleet import discover, report
from fleet import health as health_mod
from fleet import snapshot as snapshot_mod

_VALID_FILTERS = ("active", "stalled", "dead", "all")


def _build_parser() -> argparse.ArgumentParser:
    """Build the top-level argument parser with the two subcommands."""
    parser = argparse.ArgumentParser(
        prog="fleet",
        description="Multi-project health scanner for the four pipeline.",
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
    """Discover projects under *root* and assess each one."""
    projects = discover.discover(root)
    return [health_mod.assess(p.name, p.ai_dir) for p in projects]


def _cmd_status(args: argparse.Namespace) -> int:
    """Run the ``status`` subcommand; return a process exit code."""
    healths = _assess_all(args.root)
    if args.filter != "all":
        healths = [h for h in healths if h.health == args.filter]
    print(report.render_portfolio(healths))
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
    if args.command == "diff":
        return _cmd_diff(args)
    parser.error(f"unknown command: {args.command}")
    return 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
