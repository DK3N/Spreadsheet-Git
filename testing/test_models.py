"""Smoke tests for the shared data classes; also proves the test setup can import src."""
from src.models import CellChange, ChangeType, DiffResult, Row, RowChange, Table


def test_table_defaults():
    table = Table(headers=["id"], rows=[])
    assert table.delimiter == ","
    assert table.line_terminator == "\n"


def test_row_stores_cells_and_raw_values():
    row = Row(row_index=0, cells={"id": "1", "name": "Ana"}, raw_values=["1", "Ana"])
    assert row.cells["name"] == "Ana"
    assert row.raw_values == ["1", "Ana"]


def test_diff_result_holds_row_changes():
    change = RowChange(
        change_type=ChangeType.MODIFIED,
        key_value="1",
        old_index=0,
        new_index=0,
        cell_changes=[CellChange(column_value="name", old_value="Ana", new_value="Anna")],
        raw_row={"id": "1", "name": "Anna"},
    )
    diff = DiffResult(changes=[change])
    assert diff.changes[0].cell_changes[0].new_value == "Anna"
