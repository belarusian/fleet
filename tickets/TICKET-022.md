# TICKET-022: tests/test_snapshot.py — load_snapshot error paths (FileNotFoundError + malformed ValueError)

## Title
`fleet/snapshot.py` `load_snapshot` has two documented error paths that are
untested: `FileNotFoundError` for a missing file and `ValueError` for a
malformed document. `tests/test_snapshot.py` only exercises the happy path.

## Evidence
- `fleet/snapshot.py:80` — `load_snapshot` docstring states it "Raises
  ``FileNotFoundError`` if the file is missing and ``ValueError`` if the
  document is malformed."
- `fleet/snapshot.py:87-88` — `if not p.is_file(): raise
  FileNotFoundError(f"snapshot not found: {p}")`.
- `fleet/snapshot.py:90-91` — `if not isinstance(doc, dict) or "projects" not
  in doc: raise ValueError(f"malformed snapshot: {p}")`.
- `tests/test_snapshot.py` — three tests, all happy-path round-trips. No test
  asserts either exception.

## Impact
A regression in the error handling (e.g. the `is_file` check being removed, the
malformed check weakening to only test `isinstance(doc, dict)` and missing the
`"projects"` key, or the wrong exception type being raised) would let a corrupt
or missing snapshot crash with an unhelpful traceback instead of the documented
clean error. The `CLI diff` path (TICKET-021) depends on the missing-file
behavior to return exit code 2.

## Suggestion
Add tests to `tests/test_snapshot.py` that:
- call `load_snapshot(tmp_path / "missing.json")` and assert
  `pytest.raises(FileNotFoundError)` with a message containing the path;
- write a JSON file that is a list (not a dict) and assert
  `pytest.raises(ValueError)`;
- write a JSON dict that lacks the `"projects"` key and assert
  `pytest.raises(ValueError)`;
- (optional) write a dict with `"projects"` containing a non-dict entry and
  assert it is skipped without raising (pinning the
  `if isinstance(d, dict)` filter at line ~95).
