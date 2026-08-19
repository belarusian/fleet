"""fleet — a multi-project health scanner for the four pipeline.

fleet scans all project AI directories under a given root (default ``~/AI``)
and emits a one-page portfolio status table. For each project it discovers
(any subdir containing an ``ai/`` with trajectories or a gate log), it uses
the ``fourseer`` parsers to extract: last cycle number, last outcome, days
since last activity, open issue count, and a health classification
(active / stalled / dead).

Public surface:
  - fleet.discover : project AI-directory discovery under a root
  - fleet.health   : per-project health metrics + classification
  - fleet.report   : markdown portfolio table renderer
  - fleet.snapshot : snapshot save/load + diff
  - fleet.cli      : the ``fleet`` entrypoint
"""

from __future__ import annotations

import os
import sys

__version__ = "0.1.0"

# Bootstrap: make the fourseer seed package importable. fleet's only
# third-party dependency is fourseer, imported from the seed path. The seed
# path is configurable via the FLEET_SEED env var (default: the known seed).
_SEED = os.environ.get("FLEET_SEED", "/home/sasha/AI/fleet/seed")
if _SEED and _SEED not in sys.path:
    sys.path.insert(0, _SEED)

__all__ = [
    "__version__",
    "discover",
    "health",
    "report",
    "snapshot",
    "cli",
]
