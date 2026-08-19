"""Smoke test: the fleet package imports cleanly."""

import fleet


def test_import_fleet() -> None:
    """Importing fleet must succeed and expose a version."""
    assert fleet is not None
    assert isinstance(fleet.__version__, str)
    assert fleet.__version__
