"""
PURPOSE: Exports a DiffResult as a JSON report that can be saved and shared.
FUNCTIONS:
- build_report: Turns a DiffResult into a plain dict (summary counts, column changes, row changes).
- write_json_report: Writes that dict to a file as UTF-8 JSON.

Each entry in "changes" uses the same fields as testing/test_cases/*/expected_diff.json.
"""

import json
from pathlib import Path
from typing import Any, Optional

from .models import ChangeType, DiffResult, RowChange


def _summary(changes: list[RowChange]) -> dict[str, int]:
    """Counts row changes the same way the terminal summary does."""
    kinds = [c.change_type for c in changes]
    return {
        "added": kinds.count(ChangeType.INSERTED),
        "removed": kinds.count(ChangeType.DELETED),
        "modified": kinds.count(ChangeType.MODIFIED) + kinds.count(ChangeType.MOVED_AND_MODIFIED),
        "moved": kinds.count(ChangeType.MOVED),
    }


def _change(change: RowChange) -> dict[str, Any]:
    return {
        "change_type": change.change_type.value,
        "key_value": change.key_value,
        "old_index": change.old_index,
        "new_index": change.new_index,
        "cell_changes": [
            {"column_value": c.column_value, "old_value": c.old_value, "new_value": c.new_value}
            for c in change.cell_changes
        ],
        "raw_row": dict(change.raw_row),
    }


def build_report(
    diff: DiffResult,
    key_col: Optional[str] = None,
    file_a: Optional[str] = None,
    file_b: Optional[str] = None,
) -> dict[str, Any]:
    """Builds a JSON-ready dict describing every change in `diff`."""
    changes = [c for c in diff.changes if c.change_type != ChangeType.UNCHANGED]
    return {
        "file_a": file_a,
        "file_b": file_b,
        "key_col": key_col,
        "summary": _summary(changes),
        "columns": {
            "added": list(diff.added_columns),
            "removed": list(diff.removed_columns),
            "reordered": diff.columns_reordered,
        },
        "changes": [_change(c) for c in changes],
    }


def write_json_report(
    diff: DiffResult,
    path: str | Path,
    key_col: Optional[str] = None,
    file_a: Optional[str] = None,
    file_b: Optional[str] = None,
) -> None:
    """Writes the report for `diff` to `path`. Raises OSError if the file can't be written."""
    report = build_report(diff, key_col=key_col, file_a=file_a, file_b=file_b)
    text = json.dumps(report, indent=2, ensure_ascii=False) + "\n"
    Path(path).write_text(text, encoding="utf-8")
