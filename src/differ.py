"""
PURPOSE: To compare two CSV tables and produce a comprehensive diff report capturing insertions, deletions, cell modifications, and physical line reordering.[cite: 1]
FUNCTIONS:
- compute_diff: Use matcher.py results and classify each change as INSERTED, DELETED, MODIFIED, MOVED, or MOVED_AND_MODIFIED.
- diff_cells: helper function that compares corresponding columns between two matched rows to detect and list individual cell-level edits.
"""

from typing import Optional
from .models import CellChange, DiffResult, Row, Table


def diff_cells(row_a: Row, row_b: Row, headers: list[str]) -> list[CellChange]:
    """Compares columns across two rows and returns a list of modified cells."""
    # TODO: fill me out
    return []


def compute_diff(table_a: Table, table_b: Table, key_col: Optional[str] = None) -> DiffResult:
    """Computes full diff report (inserted, deleted, modified, moved) between two tables."""
    # TODO: fill me out too!
    return DiffResult(changes=[])