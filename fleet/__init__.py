"""fleet — a multi-project health scanner for the four pipeline.

fleet scans all project AI directories under a given root (default ``~/AI``)
and emits a one-page portfolio status table. For each project it discovers
(any subdir containing an ``ai/`` with trajectories or a gate log), it uses
the ``fourseer`` parsers to extract: last cycle number, last outcome, days
since last activity, open issue count, and a health classification
(active / stalled / dead).

Intended public surface (built out across cycles):
  - fleet.discover : project AI-directory discovery under a root
  - fleet.health   : per-project health classification + metrics
  - fleet.snapshot : snapshot save/load + diff
  - fleet.report   : markdown portfolio table renderer
  - fleet.cli      : the ``fleet`` entrypoint
"""

__version__ = "0.1.0"

__all__ = [
    "__version__",
]
