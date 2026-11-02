"""Shared helpers for building Tables and CSV files in tests."""
import pytest

from src.models import Row, Table


def make_table(headers, *value_rows):
    """Build a Table from headers and lists of cell values (row_index = position)."""
    rows = [
        Row(row_index=i, cells=dict(zip(headers, values)), raw_values=list(values))
        for i, values in enumerate(value_rows)
    ]
    return Table(headers=list(headers), rows=rows)


@pytest.fixture
def write_file(tmp_path):
    """Write text to a temp file and return its path. Pass data=bytes for raw bytes."""
    def _write(name, data):
        path = tmp_path / name
        if isinstance(data, bytes):
            path.write_bytes(data)
        else:
            path.write_text(data, encoding="utf-8", newline="")
        return path
    return _write
