"""
PURPOSE: Executes a 3-way merge across base, "ours", and "theirs" CSV tables.
FUNCTIONS:
- three_way_merge: Merges edits from "ours" and "theirs" tables relative to base, producing a resolved Table and flagging conflicts.
- resolve_cell: Compares base, "our", and "their" values for a specific cell to decide the final merged value or flag a MergeConflict.
"""

from typing import Optional, Tuple
from .models import MergeConflict, MergeResult, Table


def resolve_cell(
    column_name: str,
    key_value: str,
    base_val: Optional[str],
    our_val: Optional[str],
    their_val: Optional[str]
) -> Tuple[str, Optional[MergeConflict]]:
    """
    Reconciles three versions of a single cell value.
    Returns: (resolved_value_or_marker, optional_conflict_instance)
    """
    # TODO
    return ("", None)


def three_way_merge(
    base: Table,
    ours: Table,
    theirs: Table,
    key_col: str
) -> MergeResult:
    """Merges "ours" and "theirs" modifications against a common base ancestor table."""
    # TODO
    return MergeResult(merged_table=base, conflicts=[], has_conflicts=False)