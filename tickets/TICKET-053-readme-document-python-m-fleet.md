# TICKET-053: README should document `python3 -m fleet` as an invocation method

## Title
Add `python3 -m fleet` to the README's CLI section as an alternative to the
installed `fleet` console script.

## Evidence
- `fleet/__main__.py` (added in Cycle 13, TICKET-051) makes
  `python3 -m fleet` a working entrypoint, delegating to `fleet.cli:main`.
- The README's "CLI" section (lines 38-44) only shows the `fleet` console
  script form: `fleet status`, `fleet snapshot`, `fleet diff`.
- The "Development" section (lines 82-85) shows `pip install -e .` but does
  not mention that `python3 -m fleet` works without installation (as long as
  the repo root is on `PYTHONPATH`).

## Impact
- A newcomer who has not run `pip install -e .` will not discover that
  `python3 -m fleet` is a valid invocation. They will see the "No module
  named fleet" error and assume the package is broken.

## Suggestion
- In the README's "CLI" section, add a one-line note:
  "The same CLI is available as `python3 -m fleet` (no installation required,
  repo root must be on `PYTHONPATH`)."
- Optionally add a "Running without installation" subsection under
  "Development".
