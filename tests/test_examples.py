"""Example-tree validity tests.

Pins that the committed ``examples/`` tree stays valid: it is discoverable by
:func:`fleet.discover.discover` and renderable by
:func:`fleet.report.render_portfolio` without crashing.

Health values are deliberately NOT asserted: the example files' mtimes vary
across checkouts (a freshly-cloned tree shows recent activity), so the health
column is not stable. We assert discoverability + renderability + no crash.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from unittest import mock

from fleet import discover, health, report

# The committed example tree, located relative to this file (CWD-independent).
EXAMPLES = Path(__file__).resolve().parent.parent / "examples"

# The projects the example tree is expected to contain.
EXPECTED_PROJECTS = {"alpha", "beta"}

NOW = datetime(2025, 6, 1, 12, 0, 0, tzinfo=timezone.utc)


class _FakeDatetime(datetime):
    """A datetime subclass whose .now() is pinned to NOW.

    Inheriting from the real datetime keeps .fromtimestamp() (used by
    health._last_activity) working; only the clock is frozen.
    """

    @classmethod
    def now(cls, tz=None):  # noqa: ARG003 - tz ignored, we always return UTC NOW
        return NOW


def _patched_now():
    """Patch health.datetime so .now() returns the fixed NOW reference."""
    return mock.patch.object(health, "datetime", _FakeDatetime)


def test_examples_dir_exists() -> None:
    """The committed examples/ tree is present in the repo."""
    assert EXAMPLES.is_dir(), f"missing example tree at {EXAMPLES}"


def test_examples_discoverable() -> None:
    """Every expected example project is discovered by the real discover."""
    projects = discover.discover(EXAMPLES)
    names = {p.name for p in projects}
    assert EXPECTED_PROJECTS <= names, f"expected {EXPECTED_PROJECTS}, found {names}"


def test_examples_renderable() -> None:
    """The full pipeline (discover -> assess -> render) yields a table with every project."""
    projects = discover.discover(EXAMPLES)
    with mock.patch.object(health, "count_open_issues", return_value=0), _patched_now():
        assessed = [health.assess(p.name, p.ai_dir) for p in projects]

    md = report.render_portfolio(assessed)

    # Header row is present.
    assert "| Project | Last Cycle | Last Outcome |" in md
    # Every discovered project appears as a row.
    for name in EXPECTED_PROJECTS:
        assert f"| {name} |" in md, f"project {name!r} missing from rendered table"


def test_examples_assess_does_not_crash() -> None:
    """Assessing every example project completes without raising (no crash)."""
    projects = discover.discover(EXAMPLES)
    assert projects, "expected at least one example project"
    with mock.patch.object(health, "count_open_issues", return_value=0), _patched_now():
        for p in projects:
            h = health.assess(p.name, p.ai_dir)
            # Each assessed project reports a valid health label.
            assert h.health in {"active", "stalled", "dead"}
