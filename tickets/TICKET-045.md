# TICKET-045 — examples/ self-contained tree

**Cycle:** 11 (Polish + Release, part 2)
**Type:** examples
**Status:** open

## Problem
There is no `examples/` tree. A reader cannot run `fleet status --root examples/`
to see real output.

## Target
Add a small, self-contained example project tree under `examples/` (the
directory itself is the scan root). At least two projects, each `<name>/ai/`
with a `trajectories/trajectory_0000.json` (valid fourseer trajectory JSON:
`{"outcome": "exit:task_complete", "messages": [{"role": "assistant", "content": "..."}]}`),
plus one project that also has a `cycle-001-gate.md` gate log and one that also
has a `cycles.out`.

## Constraints
- The trajectory JSON, `cycles.out` header (`========== CYCLE 1  HH:MM:SSZ
  ==========` + two `OUTER` lines), and gate log (`## Cycle 1` block) must all
  parse without error (see seed parse/trajectories.py, parse/cycles_out.py,
  parse/gate_log.py).
- Keep it minimal and realistic.
- Verify by running `fleet status --root examples/` locally before committing.

## Acceptance
- `examples/` exists with 2+ projects, each discoverable.
- `fleet status --root examples/` runs without error and lists every project.
- Gate green (pytest + ruff + mypy).
