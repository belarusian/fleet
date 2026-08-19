# TICKET-008: discover.py — Make the final sort fully deterministic (name, then path)

## Title
`discover` sorts by `name` only. Two projects with the same basename at different depths (e.g. `<root>/a/ai` and `<root>/g/a/ai`) would tie on `name`, leaving their relative order dependent on insertion order.

## Evidence
`fleet/discover.py::discover` ends with `found.sort(key=lambda p: p.name)`. The depth-1 and depth-2 passes append in a fixed order, but a name collision across depths is not explicitly ordered.

## Impact
- Output order is not guaranteed stable for same-named projects at different depths; a portfolio table could reorder between runs if the walk order ever changes.

## Suggestion
1. Change the final sort to `found.sort(key=lambda p: (p.name, str(p.path)))` so ties break deterministically by path.
2. Add a test that two same-named projects at different depths come back in a stable, path-ordered sequence.
