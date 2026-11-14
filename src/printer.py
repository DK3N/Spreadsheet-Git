
"""
PURPOSE: Prints DiffResult / MergeResult data structures into something
the user can understand, such as ANSI colorized terminal logs and inline
CSV conflict markers.

FUNCTIONS:
- render_diff_terminal: Displays row changes and column changes in the terminal.
- format_conflict_marker: Generates a Git-style inline merge conflict string.
"""

from .models import ChangeType, DiffResult, RowChange

RED = "\033[31m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
CYAN = "\033[36m"
RESET = "\033[0m"

STYLE = {
    ChangeType.INSERTED: (GREEN, "+"),
    ChangeType.DELETED: (RED, "-"),
    ChangeType.MODIFIED: (YELLOW, "~"),
    ChangeType.MOVED: (CYAN, ">"),
    ChangeType.MOVED_AND_MODIFIED: (YELLOW, "~>"),
}


def _paint(text: str, color: str, use_color: bool) -> str:
    """Wraps text in an ANSI color code, or returns it unchanged if color is off."""
    return f"{color}{text}{RESET}" if use_color else text


def _location(change: RowChange) -> str:
    """Describes where the row was, using whichever indexes are available."""
    old, new = change.old_index, change.new_index
    if old is not None and new is not None:
        return f"row {old + 2} -> row {new + 2}"
    if old is not None:
        return f"was row {old + 2}"
    if new is not None:
        return f"now row {new + 2}"
    return ""


def _render_row(change: RowChange, use_color: bool) -> list[str]:
    """Turns one RowChange into one or more lines of text."""
    color, symbol = STYLE[change.change_type]
    label = change.change_type.value.replace("_", " ")
    header = f"{symbol} {label}  key={change.key_value}  ({_location(change)})"
    lines = [_paint(header, color, use_color)]

    for cell in change.cell_changes:
        detail = f"    {cell.column_value}: {cell.old_value!r} -> {cell.new_value!r}"
        lines.append(_paint(detail, color, use_color))

    return lines


def format_conflict_marker(our_val: str, their_val: str) -> str:
    """Wraps two divergent values in inline Git-style conflict boundary markers."""
    return f"<<<<<<< OURS: {our_val} ======= THEIRS: {their_val} >>>>>>>"


def render_diff_terminal(diff: DiffResult, use_color: bool = True) -> str:
    """Displays row changes and column changes in the terminal."""

    changes = [c for c in diff.changes if c.change_type != ChangeType.UNCHANGED]

    # Check if any columns were added, removed, or reordered
    has_column_changes = (
        diff.added_columns
        or diff.removed_columns
        or diff.columns_reordered
    )

    # Only say no differences if neither rows nor columns changed
    if not changes and not has_column_changes:
        return "No differences found."

    lines: list[str] = []

    # Display changes to the CSV columns
    if has_column_changes:
        lines.append("Column Changes:")

        for column in diff.added_columns:
            lines.append(
                _paint(f"+ Column added: {column}", GREEN, use_color)
            )

        for column in diff.removed_columns:
            lines.append(
                _paint(f"- Column removed: {column}", RED, use_color)
            )

        if diff.columns_reordered:
            lines.append(
                _paint("> Columns reordered", CYAN, use_color)
            )

        lines.append("")

    # Display the existing row changes
    if changes:
        if has_column_changes:
            lines.append("Row Changes:")

        for change in changes:
            lines.extend(_render_row(change, use_color))

        kinds = [c.change_type for c in changes]
        added = kinds.count(ChangeType.INSERTED)
        removed = kinds.count(ChangeType.DELETED)
        modified = kinds.count(ChangeType.MODIFIED) + kinds.count(ChangeType.MOVED_AND_MODIFIED)
        moved = kinds.count(ChangeType.MOVED)

        summary = f"{added} added, {removed} removed, {modified} modified"

        if moved:
            summary += f", {moved} moved"

        lines.append("")
        lines.append(f"Summary: {summary}")

    else:
        lines.append("No row changes detected.")

    return "\n".join(lines)
