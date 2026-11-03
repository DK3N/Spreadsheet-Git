"""
PURPOSE: To pair corresponding rows between two CSV tables across physical moves, using either a user-defined primary key or guess if there's nothing.
FUNCTIONS:
- match_rows: Matches rows between two Table objects based on a key column or some kind of similarity metric.
- compute_row_similarity: Calculates the proportion of matching cell values between two rows to evaluate whether a row was moved and modified.
"""
from .models import Row, Table
from typing import Optional

def match_rows(
    table_a: Table,
    table_b: Table,
    key_col: Optional[str] = None,
    threshold: float = 0.7
) -> tuple[list[tuple[Row, Row]], list[Row], list[Row]]:
    """
    Pairs corresponding rows between two tables.
    Returns: (matched_pairs, unmatched_a_deletions, unmatched_b_insertions)
    """

    if not 0.0 <= threshold <= 1.0:
        return ValueError("threshold must be between 0.0 and 1.0")
    

    if key_col is not None:
        if key_col not in table_a.headers or key_col not in table_b.headers:
            return ValueError(f"Key Column {key_col!r} must exist in both tables")
    
        # takes in a table, returns a dictionary where key = CSV table key, value = row
        # also checks if every row has a unique key_col
        def index_by_key(table: Table) -> dict[str,Row]:
            rows_by_key: dict[str, Row] = {}

            for row in table.rows:
                value = row.cells.get(key_col)
                if value is None or not value.strip():
                    raise ValueError(
                        f"Key column {key_col!r} has a blank value "
                        f"at row {row.row_index}"
                    )
                if value in rows_by_key:
                    return ValueError(
                        f"Key column {key_col!r} has duplicate value {value!r}"
                    )
                rows_by_key[value] = row
            return rows_by_key
        
        # get a dictionary of rows for each table here
        rows_a = index_by_key(table_a)
        rows_b = index_by_key(table_b)

        # find the matching rows according to key_col
        matched_pairs = [
            (row, rows_b[key])
            for row in table_a.rows
            if (key := row.cells[key_col]) in rows_b
        ]
        matched_keys = {row.cells[key_col] for row, _ in matched_pairs}
        
        # create the unmatched lists according to rows not found in the other table
        unmatched_a = [row for row in table_a.rows if row.cells[key_col] not in rows_b]
        unmatched_b = [row for row in table_b.rows if row.cells[key_col] not in matched_keys]

        return matched_pairs, unmatched_a, unmatched_b
    else:
        shared_headers = [
            header for header in table_a.headers
            if header in table_b.headers
        ]
        if not shared_headers:
            return [], table_a.rows.copy(), table_b.rows.copy()
        
        # create the candidates list based on rows from each table and compute_row_similarity
        candidates = [
            (
                compute_row_similarity(row_a, row_b, shared_headers),
                index_a,
                index_b,
            )
            for index_a, row_a in enumerate(table_a.rows)
            for index_b, row_b in enumerate(table_b.rows)
        ]
        # filter the candidates list according to the threshold, and sort contents
        candidates = [
            candidate for candidate in candidates if candidate[0] >= threshold
        ]
        candidates.sort(key=lambda candidate: (-candidate[0], candidate[1], candidate[2]))

        # create the list of index_a and index_b tuples
        matched_indices: list[tuple[int, int]] = []
        matched_a: set[int] = set()
        matched_b: set[int] = set()

        # populate the lists we just made if both indices haven't been matched yet
        for _, index_a, index_b in candidates:
            if index_a not in matched_a and index_b not in matched_b:
                matched_indices.append((index_a, index_b))
                matched_a.add(index_a)
                matched_b.add(index_b)
        
        matched_indices.sort()
        
        # prepare final answers

        # populates matched_pairs based on matched_indices list
        matched_pairs = [
            (table_a.rows[index_a], table_b.rows[index_b])
            for index_a, index_b in matched_indices
        ]
        # populates unmatched_a if a row from table_a can't be found in matched_a
        unmatched_a = [
            row for index, row in enumerate(table_a.rows)
            if index not in matched_a
        ]
        unmatched_b = [
            row for index, row in enumerate(table_b.rows)
            if index not in matched_b
        ]

        return matched_pairs, unmatched_a, unmatched_b

def compute_row_similarity(row_a: Row, row_b: Row, headers: list[str]) -> float:
    """Calculates cell-level similarity ratio (0.0 to 1.0) between two rows across common columns."""
    if not headers:
        return 0.0
    matches = sum(
        row_a.cells.get(header, "") == rows_b.cells.get(header, "")
        for header in headers
    )
    return matches / len(headers)