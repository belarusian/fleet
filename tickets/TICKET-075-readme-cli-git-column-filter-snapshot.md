# TICKET-075: Document the v2 CLI surface (Git column, --filter, snapshot health_v2)

## Title
The README's CLI section still shows the v1 `--filter active|stalled|dead|all`
and says nothing about the `Git` column, the `stranded`/`paused` filter
values, or the `health_v2` snapshot field. Update it to match the shipped v2
CLI behavior.

## Evidence
- `fleet/cli.py` — `_VALID_FILTERS = ("active", "stalled", "dead", "stranded",
  "paused", "all")`; `_cmd_status` selects `stranded`/`paused` with
  `classify_health_v2` over each project's git state, and the v1 classes match
  the `Health` column.
- `fleet/cli.py` — `_cmd_status` always passes `git_states` to
  `render_portfolio`, so the `status` table always shows a trailing `Git`
  column.
- `fleet/report.py` — `_fmt_git` renders `unmerged:<b1>+<b2>` / `unpushed:<n>`
  / `-` when clean.
- `fleet/snapshot.py` — `save_snapshot(..., git_states=...)` stores a per-row
  `health_v2`; `_field_changes` surfaces a `health_v2 <a>-><b>` fragment
  (`-` for `None`); `_health_from_dict` reads `health_v2=d.get("health_v2")`
  so old v1 snapshots load with `health_v2 is None`.

## Change
- Update the `status` usage line to
  `[--filter active|stalled|dead|stranded|paused|all]`.
- Note that the `status` table always shows a trailing `Git` column
  (`unmerged:<branch>` / `unpushed:<n>` / `-` when clean) and that
  `stranded`/`paused` are selected with the v2 classifier over the git state.
- Note that `snapshot` now stores a per-row `health_v2` field and `diff`
  surfaces a `health_v2 <a>-><b>` fragment (`-` for `None`), and that old v1
  snapshots still load with `health_v2` defaulting to `None`.

## Acceptance
- README CLI section matches the shipped v2 CLI: filter choices, the always-on
  `Git` column, and the snapshot `health_v2` field.
