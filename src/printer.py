"""
PURPOSE: Prints DiffResult / MergeResult data structures into something the user can understand, such as ANSI colorized terminal logs and inline CSV conflict markers.
FUNCTIONS:
- render_diff_terminal: Formats a DiffResult into human-readable, color-coded terminal output detailing row movements, edits, additions, and deletions.
- format_conflict_marker: Generates a Git-style inline merge conflict string inside a single cell when two collaborators submit conflicting edits.
"""

from .models import DiffResult


def format_conflict_marker(our_val: str, their_val: str) -> str:
    """Wraps two divergent values in inline Git-style conflict boundary markers."""
    # TODO: Return formatted conflict marker string
    return f"<<<<<<< OURS: {our_val} ======= THEIRS: {their_val} >>>>>>>"


def render_diff_terminal(diff: DiffResult) -> str:
    """Generates a color-coded ANSI terminal representation of a DiffResult."""
    # TODO: Iterate diff.changes and format lines with color tags
    return ""