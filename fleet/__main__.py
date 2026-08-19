"""Allow ``python3 -m fleet`` to invoke the CLI.

This module exists solely so that the package can be executed as a script
module. It delegates to :func:`fleet.cli.main`, which is the same entry
point used by the ``fleet`` console script (see ``pyproject.toml``
``[project.scripts]``).
"""

from __future__ import annotations

import sys

from fleet.cli import main

if __name__ == "__main__":
    sys.exit(main())
