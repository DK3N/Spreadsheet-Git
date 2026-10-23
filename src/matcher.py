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
    # TODO: Match using key_col if provided; fallback to compute_row_similarity
    return ([], [], [])

def compute_row_similarity(row_a: Row, row_b: Row, headers: list[str]) -> float:
    """Calculates cell-level similarity ratio (0.0 to 1.0) between two rows across common columns."""
    # TODO: Calculate Jaccard or exact matching proportion over columns
    return 0.0