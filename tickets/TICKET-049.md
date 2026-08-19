# TICKET-049: Add a CHANGELOG.md summarizing the shipped capability

## Title
A `CHANGELOG.md` at the repo root documenting what `fleet` ships in 0.1.0.

## Evidence
- No `CHANGELOG.md` existed at the repo root before this change.
- The capability shipped across the 12 build cycles (see the cycle log):
  discovery, health metrics, classification, report, CLI (status/diff/snapshot),
  snapshot, robustness, docs, and examples — all merged on main.

## Change
- New `CHANGELOG.md`: a `# Changelog` header, a `## [0.1.0] - 2026-08-19`
  release section, and a concise bullet list of the shipped capability grouped
  by area (Discovery, Health metrics, Classification, Report, Snapshot, CLI,
  Robustness, Docs, Examples, Release), plus a short Notes section (open_issues
  is 0 in CLI output by design; `--json` was considered and declined).
- Every listed capability is cross-checked against the merged source on main
  (no invented features).

## Acceptance
- `CHANGELOG.md` exists at the repo root.
- It lists only capabilities actually merged on main.
- The release date matches the actual date (2026-08-19).
