"""
PURPOSE: To hold data classes that will be used throughout our project.
FUNCTIONS: none, really.
Contains Row, Table, CellChange, RowChange, MergeConflict, MergeResults, DiffResults
"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional, Any

class ChangeType(Enum):
    """
    A lil Enum storing all the different change types
    """
    UNCHANGED = "UNCHANGED"
    INSERTED = "INSERTED"
    DELETED = "DELETED"
    MODIFIED = "MODIFIED"
    MOVED = "MOVED"
    MOVED_AND_MODIFIED = "MOVED_AND_MODIFIED"

@dataclass
class Row:
    """
    Stores a dictionary of cell values (Key is the column header name, Value is...the value).
    Stores the raw string values from the CSV and the row index of the ORIGINAL CSV FILE,
    not necessarily the Table object that holds it.
    """
    row_index: int
    cells: dict[str, str]
    raw_values: list[str]

@dataclass
class Table:
    """
    Each table stores the headers, and the Row objects that populate it
    Also stores how we define the end of a line or the end of a value
    """
    headers: list[str]
    rows: list[Row]
    delimiter: str = ","
    line_terminator: str = "\n"

@dataclass
class CellChange:
    """
    Stores a cell's old value and new value (and where to find it)
    """
    column_value: str
    old_value: str
    new_value: str

# stores all the cell changes in a row,
# and its old row index and new row index (if it was moved)
@dataclass
class RowChange:
    """
    Stores all the cell changes and the change type (modified, deleted, moved, etc)
    If this row was moved, it stores the old row index and the new row index
    """
    change_type: ChangeType
    key_value: Any
    old_index: Optional[int]
    new_index: Optional[int]
    cell_changes: list[CellChange]
    raw_row: dict[str, str]

@dataclass
class MergeConflict:
    """
    Stores the three relevant values of a cell: The base version, our new version, and "their" new version
    Also stores where this merge conflict occurs
    """
    key_value: Any
    column_name: str
    base_val: str
    our_val: str
    their_val: str

@dataclass
class DiffResult:
    """
    A list of row changes
    """
    changes: list[RowChange]

@dataclass
class MergeResult:
    """
    Stores the results of a merge: the table, and a list of any merge conflicts.
    """
    merged_table: Table
    conflicts: list[MergeConflict]
    has_conflicts: bool