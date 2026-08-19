"""Smoke test: the fleet package imports cleanly and exposes its surface."""

import fleet


def test_import_fleet() -> None:
    """Importing fleet must succeed and expose a version."""
    assert fleet is not None
    assert isinstance(fleet.__version__, str)
    assert fleet.__version__


def test_submodules_import() -> None:
    """All public submodules import and expose their key symbols."""
    from fleet import cli, discover, health, report, snapshot  # noqa: F401

    assert discover.discover is not None
    assert health.assess is not None
    assert report.render_portfolio is not None
    assert snapshot.load_snapshot is not None
    assert cli.main is not None
