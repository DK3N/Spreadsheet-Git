"""
PURPOSE: To compare two CSV tables and produce a comprehensive diff report capturing insertions, deletions, cell modifications, and physical line reordering.
FUNCTIONS:
- compute_diff: Use matcher.py results and classify each change as INSERTED, DELETED, MODIFIED, MOVED, or MOVED_AND_MODIFIED.
- diff_cells: helper function that compares corresponding columns between two matched rows to detect and list individual cell-level edits.
"""

from bisect import bisect_left
from typing import Optional

from .matcher import match_rows
from .models import CellChange, ChangeType, DiffResult, Row, RowChange, Table


def diff_cells(row_a: Row, row_b: Row, headers: list[str]) -> list[CellChange]:
    """Compares columns across two rows and returns a list of modified cells."""
    changes: list[CellChange] = []
    for col in headers:
        old = row_a.cells.get(col, "")
        new = row_b.cells.get(col, "")
        if old != new:
            changes.append(CellChange(column_value=col, old_value=old, new_value=new))
    return changes


def _merged_headers(table_a: Table, table_b: Table) -> list[str]:
    return list(dict.fromkeys(table_a.headers + table_b.headers))


def _check_key_col(table: Table, key_col: Optional[str]) -> None:
    if key_col is not None and table.rows and key_col not in table.headers:
        raise ValueError(f"key column {key_col!r} not found in headers {table.headers}")


def _check_each_row_returned_once(table: Table, returned: list[Row], name: str) -> None:
    if sorted(r.row_index for r in returned) != sorted(r.row_index for r in table.rows):
        raise ValueError(
            f"match_rows must return each row of {name} exactly once, "
            f"but returned {len(returned)} row(s) for {len(table.rows)} row(s) in the table"
        )


def _longest_increasing_positions(values: list[int]) -> set[int]:
    tails: list[int] = []
    tails_pos: list[int] = []
    parent = [-1] * len(values)
    for pos, val in enumerate(values):
        k = bisect_left(tails, val)
        if k == len(tails):
            tails.append(val)
            tails_pos.append(pos)
        else:
            tails[k] = val
            tails_pos[k] = pos
        parent[pos] = tails_pos[k - 1] if k > 0 else -1

    positions: set[int] = set()
    pos = tails_pos[-1] if tails_pos else -1
    while pos != -1:
        positions.add(pos)
        pos = parent[pos]
    return positions


def _stable_pair_positions(pairs: list[tuple[Row, Row]]) -> set[int]:
    by_new_index = sorted(range(len(pairs)), key=lambda i: pairs[i][1].row_index)
    old_indices = [pairs[i][0].row_index for i in by_new_index]
    return {by_new_index[pos] for pos in _longest_increasing_positions(old_indices)}


def _key_of(row: Row, key_col: Optional[str]) -> str | int:
    if key_col is not None and key_col in row.cells:
        return row.cells[key_col]
    return row.row_index


def _row_change(
    kind: ChangeType,
    row: Row,
    key_col: Optional[str],
    old_index: Optional[int],
    new_index: Optional[int],
    cell_changes: Optional[list[CellChange]] = None,
) -> RowChange:
    return RowChange(
        change_type=kind,
        key_value=_key_of(row, key_col),
        old_index=old_index,
        new_index=new_index,
        cell_changes=cell_changes or [],
        raw_row=dict(row.cells),
    )


def compute_diff(table_a: Table, table_b: Table, key_col: Optional[str] = None) -> DiffResult:
    """Computes full diff report (inserted, deleted, modified, moved) between two tables."""
    _check_key_col(table_a, key_col)
    _check_key_col(table_b, key_col)

    pairs, deleted, inserted = match_rows(table_a, table_b, key_col=key_col)
    _check_each_row_returned_once(table_a, [row_a for row_a, _ in pairs] + deleted, "table_a")
    _check_each_row_returned_once(table_b, [row_b for _, row_b in pairs] + inserted, "table_b")

    headers = _merged_headers(table_a, table_b)
    stable = _stable_pair_positions(pairs)

    changes: list[RowChange] = []

    for i, (row_a, row_b) in enumerate(pairs):
        cell_changes = diff_cells(row_a, row_b, headers)
        moved = i not in stable
        if moved and cell_changes:
            kind = ChangeType.MOVED_AND_MODIFIED
        elif moved:
            kind = ChangeType.MOVED
        elif cell_changes:
            kind = ChangeType.MODIFIED
        else:
            continue
        changes.append(_row_change(kind, row_b, key_col, row_a.row_index, row_b.row_index, cell_changes))

    for row in inserted:
        changes.append(_row_change(ChangeType.INSERTED, row, key_col, None, row.row_index))

    changes.sort(key=lambda c: c.new_index)

    for row in sorted(deleted, key=lambda r: r.row_index):
        changes.append(_row_change(ChangeType.DELETED, row, key_col, row.row_index, None))

    return DiffResult(changes=changes)
