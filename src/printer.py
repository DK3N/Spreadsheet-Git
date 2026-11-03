"""
PURPOSE: Prints DiffResult / MergeResult data structures into something the user can understand, such as ANSI colorized terminal logs and inline CSV conflict markers.
FUNCTIONS:
- render_diff_terminal: Formats a DiffResult into human-readable, color-coded terminal output detailing row movements, edits, additions, and deletions.
- format_conflict_marker: Generates a Git-style inline merge conflict string inside a single cell when two collaborators submit conflicting edits.
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
        return f"row {old} -> row {new}"
    if old is not None:
        return f"was row {old}"
    if new is not None:
        return f"now row {new}"
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
    """Generates a color-coded ANSI terminal representation of a DiffResult."""
    changes = [c for c in diff.changes if c.change_type != ChangeType.UNCHANGED]
    if not changes:
        return "No differences found."

    lines: list[str] = []
    counts: dict[str, int] = {}
    for change in changes:
        lines.extend(_render_row(change, use_color))
        name = change.change_type.value.lower().replace("_", " ")
        counts[name] = counts.get(name, 0) + 1

    summary = ", ".join(f"{n} {name}" for name, n in counts.items())
    lines.append("")
    lines.append(f"Summary: {summary}")
    return "\n".join(lines) 