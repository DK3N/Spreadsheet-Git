"""
PURPOSE: Convert CSV files into Table/Row objects and back.

Supports:
- Comma-separated files with headers
- Quoted commas, quotes, and line breaks
- UTF-8 files with or without a BOM
- Clear errors for invalid headers and jagged rows
"""

import csv
from pathlib import Path

from .models import Row, Table


def read_csv(file_path: str | Path) -> Table:
    """Read a CSV file into a Table. Data row indexes start at zero."""
    rows = []

    with open(file_path, "r", encoding="utf-8-sig", newline="") as file:
        reader = csv.reader(file, delimiter=",", strict=True)

        try:
            headers = next(reader, None)

            if headers is None:
                raise ValueError("The CSV file is empty and has no headers.")

            if not headers or any(not header.strip() for header in headers):
                raise ValueError("Each column must have a nonempty header.")

            if len(headers) != len(set(headers)):
                raise ValueError("Column headers must be unique.")

            for values in reader:
                # Ignore completely blank lines.
                # A row such as ",," still contains empty cell values.
                if not values:
                    continue

                if len(values) != len(headers):
                    raise ValueError(
                        f"Row ending at line {reader.line_num} has "
                        f"{len(values)} values; expected {len(headers)}."
                    )

                rows.append(
                    Row(
                        row_index=len(rows),
                        cells=dict(zip(headers, values)),
                        raw_values=values.copy(),
                    )
                )

        except csv.Error as error:
            raise ValueError(
                f"Invalid CSV near line {reader.line_num}: {error}"
            ) from error

    return Table(headers=headers, rows=rows)


def write_csv(table: Table, output_path: str | Path) -> None:
    """Write a Table to a CSV file using its current cell values."""
    with open(output_path, "w", encoding="utf-8", newline="") as file:
        writer = csv.writer(
            file,
            delimiter=table.delimiter,
            lineterminator=table.line_terminator,
            quoting=csv.QUOTE_MINIMAL,
        )

        writer.writerow(table.headers)

        for row in table.rows:
            writer.writerow([
                row.cells.get(header, "")
                for header in table.headers
            ])
