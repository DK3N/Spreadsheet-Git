"""
PURPOSE: Executes a 3-way merge across base, "ours", and "theirs" CSV tables.
FUNCTIONS:
- three_way_merge: Merges edits from "ours" and "theirs" tables relative to base, producing a resolved Table and flagging conflicts.
- resolve_cell: Compares base, "our", and "their" values for a specific cell to decide the final merged value or flag a MergeConflict.

Rules:
- A cell changed on only one side takes that side's value.
- A cell changed the same way on both sides takes that value.
- A cell changed differently on both sides is a conflict: the cell gets a Git-style
  marker and a MergeConflict is recorded.
- A row added on either side is kept. If both sides add the same key, the two
  versions are merged cell by cell with no base (any difference is a conflict).
- A row deleted on one side and unchanged on the other is removed (columns the
  other side added don't count as edits). Deleted on one side but edited on the
  other is a conflict: the edited row is kept and each edited cell is marked, with
  "<deleted>" as the deleting side's value.
- Columns are the base columns, then columns added in ours, then columns added in
  theirs. A base column removed on one side is dropped if the other side left it
  untouched. If the other side edited it, the column is kept so those edits are not
  lost: the removing side counts as "" and the edited cells become conflicts.
  A cell missing from a version counts as "".
- Row order follows ours, then rows that only exist in theirs, in theirs' order.
"""

from typing import Optional, Tuple

from .matcher import match_rows
from .models import MergeConflict, MergeResult, Row, Table
from .printer import format_conflict_marker

DELETED = "<deleted>"


def resolve_cell(
    column_name: str,
    key_value: str,
    base_val: Optional[str],
    our_val: Optional[str],
    their_val: Optional[str]
) -> Tuple[str, Optional[MergeConflict]]:
    """
    Reconciles three versions of a single cell value.
    None means the cell does not exist in that version.
    Returns: (resolved_value_or_marker, optional_conflict_instance)
    """
    if our_val == their_val:
        return (our_val or "", None)
    if our_val == base_val:
        return (their_val or "", None)
    if their_val == base_val:
        return (our_val or "", None)
    conflict = MergeConflict(
        key_value=key_value,
        column_name=column_name,
        base_val=base_val or "",
        our_val=our_val or "",
        their_val=their_val or "",
    )
    return (format_conflict_marker(conflict.our_val, conflict.their_val), conflict)


def _by_key(table: Table, key_col: str) -> dict[str, Row]:
    return {row.cells[key_col]: row for row in table.rows}


def _edited_column(col: str, base: Table, other: Table, key_col: str) -> bool:
    """True if `other` has any value in `col` that differs from base (new rows included)."""
    base_rows = _by_key(base, key_col)
    for row in other.rows:
        b = base_rows.get(row.cells[key_col])
        if row.cells.get(col, "") != (b.cells.get(col, "") if b else ""):
            return True
    return False


def _headers(base: Table, ours: Table, theirs: Table, key_col: str) -> list[str]:
    headers = []
    for col in base.headers:
        in_ours, in_theirs = col in ours.headers, col in theirs.headers
        if in_ours and in_theirs:
            headers.append(col)
        elif in_ours or in_theirs:
            # Removed on one side: drop it only if the other side didn't touch it.
            other = ours if in_ours else theirs
            if _edited_column(col, base, other, key_col):
                headers.append(col)
    for col in ours.headers + theirs.headers:
        if col not in headers and col not in base.headers:
            headers.append(col)
    return headers


def _unchanged(base_row: Row, other_row: Row, headers: list[str]) -> bool:
    return all(base_row.cells.get(h, "") == other_row.cells.get(h, "") for h in headers)


def three_way_merge(
    base: Table,
    ours: Table,
    theirs: Table,
    key_col: str
) -> MergeResult:
    """Merges "ours" and "theirs" modifications against a common base ancestor table."""
    # match_rows validates the key column (exists, no blanks, no duplicates).
    match_rows(base, ours, key_col=key_col)
    match_rows(base, theirs, key_col=key_col)

    headers = _headers(base, ours, theirs, key_col)
    base_cols = [h for h in headers if h in base.headers]
    base_rows = _by_key(base, key_col)
    our_rows = _by_key(ours, key_col)
    their_rows = _by_key(theirs, key_col)

    # Rows deleted on both sides are in neither list, so they drop out here.
    order = list(our_rows) + [k for k in their_rows if k not in our_rows]

    merged: list[dict[str, str]] = []
    conflicts: list[MergeConflict] = []

    for key in order:
        b, o, t = base_rows.get(key), our_rows.get(key), their_rows.get(key)

        if b is not None and (o is None or t is None):
            survivor = o if o is not None else t
            if _unchanged(b, survivor, base_cols):
                continue  # deleted on one side, untouched on the other
            cells = {}
            for col in headers:
                base_val = b.cells.get(col, "")
                kept_val = survivor.cells.get(col, "")
                if kept_val == base_val:
                    cells[col] = kept_val
                    continue
                our_val = kept_val if o is not None else DELETED
                their_val = kept_val if t is not None else DELETED
                conflict = MergeConflict(key, col, base_val, our_val, their_val)
                conflicts.append(conflict)
                cells[col] = format_conflict_marker(our_val, their_val)
            merged.append(cells)
            continue

        if o is None or t is None:
            merged.append({col: (o or t).cells.get(col, "") for col in headers})
            continue  # added on one side only

        cells = {}
        for col in headers:
            base_val = b.cells.get(col, "") if b is not None else None
            value, conflict = resolve_cell(
                col, key, base_val, o.cells.get(col, ""), t.cells.get(col, "")
            )
            cells[col] = value
            if conflict:
                conflicts.append(conflict)
        merged.append(cells)

    rows = [
        Row(row_index=i, cells=cells, raw_values=[cells[h] for h in headers])
        for i, cells in enumerate(merged)
    ]
    table = Table(
        headers=headers,
        rows=rows,
        delimiter=base.delimiter,
        line_terminator=base.line_terminator,
    )
    return MergeResult(merged_table=table, conflicts=conflicts, has_conflicts=bool(conflicts))
