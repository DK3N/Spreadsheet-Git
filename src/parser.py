"""
PURPOSE: Conversion between raw CSV text on disk and structured Table/Row model
FUNCTIONS:
- read_csv: Reads and parses a CSV file into a Table and Row objects, handling RFC 4180 rules, UTF-8 BOM, and jagged rows.
- write_csv: Serializes a Table and Row objects back into a valid CSV file.
"""
import csv
from pathlib import Path
from .models import Row, Table

def read_csv(file_path: str | Path) -> Table:
    """Reads a CSV file, and returns a populated Table instance."""
    # TODO
    return Table(headers=[], rows=[])

def write_csv(table: Table, output_path: str | Path) -> None:
    """Serializes a Table object back to disk at output_path."""
    # TODO: this one too!
    return None