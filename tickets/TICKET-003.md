# TICKET-003: health.py — `days_since_activity` edge cases produce negative or zero values

## Title
The `days_since_activity` computation does not handle (a) future-dated timestamps, (b) same-day activity, or (c) missing `last_activity` field.

## Evidence
`fleet/health.py` — the line computing days-since-activity (approximately):