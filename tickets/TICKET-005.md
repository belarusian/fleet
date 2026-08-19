# TICKET-005: discover.py — No handling of partially-written or corrupt trajectory files

## Title
Discovery and health extraction assume every file under the trajectory root is a valid, complete JSON/JSONL record. A partially-written file (crash mid-write) or a corrupt file causes the entire health extraction to fail or silently skip data.

## Evidence
`fleet/discover.py` — the file-reading loop (e.g. `for path in glob(root + "/*.json"): json.load(open(path))`) has no:
- `try/except (json.JSONDecodeError, OSError)` around individual file reads
- File-size or mtime check to detect a file that is still being written (e.g. size is 0 or mtime is within the last 2 seconds)
- Fallback or quarantine for unreadable files

`fleet/health.py` inherits this: if one trajectory file is corrupt, the exception propagates and the entire health snapshot is lost (or, if caught upstream, the metric set is silently incomplete with no indication of which file was skipped).

## Impact
- A single corrupt file (disk error, interrupted write, manual edit) takes down the entire health report.
- Operators see either a crash traceback or a health report with fewer trajectories than expected, with no explanation.
- In a fleet of many agents, one bad file on one node can mask a real health regression on another.

## Suggestion
1. Wrap per-file reads in a `try/except` that logs a `WARNING` with the file path and exception, then continues: