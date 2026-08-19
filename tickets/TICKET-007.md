# TICKET-007: discover.py — Add `ProjectRef` alias for `Project`

## Title
The cycle-1 briefing named the discovery return type `ProjectRef`, but the code defines `Project`. The alias is missing.

## Evidence
`fleet/discover.py` defines `@dataclass(frozen=True) class Project` and `discover(root) -> list[Project]`. No `ProjectRef` symbol exists.

## Impact
- Callers referencing the briefing-named type `ProjectRef` get a `NameError`.
- Minor API-parity gap; no behavioral bug.

## Suggestion
1. Add `ProjectRef = Project` at module scope in `fleet/discover.py` (a true alias, not a subclass).
2. Add a test `test_project_ref_alias` asserting `discover.ProjectRef is discover.Project`.
