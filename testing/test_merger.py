"""Tests for src/merger.py (card #1170: 3-way merge with conflict flagging)."""
import pytest

from src.cli import EXIT_CONFLICTS, EXIT_ERROR, EXIT_OK, main
from src.merger import resolve_cell, three_way_merge
from src.parser import read_csv
from src.printer import format_conflict_marker
from conftest import make_table

H = ["id", "name", "qty"]
BASE = make_table(H, ["1", "apple", "5"], ["2", "pear", "3"], ["3", "plum", "8"])


def rows(result):
    return [[r.cells[h] for h in result.merged_table.headers] for r in result.merged_table.rows]


# ---------- resolve_cell ----------

@pytest.mark.parametrize("base, ours, theirs, expected", [
    ("a", "a", "a", "a"),   # untouched
    ("a", "b", "a", "b"),   # only ours changed
    ("a", "a", "c", "c"),   # only theirs changed
    ("a", "b", "b", "b"),   # both changed the same way
])
def test_resolve_cell_without_conflict(base, ours, theirs, expected):
    assert resolve_cell("col", "1", base, ours, theirs) == (expected, None)


def test_resolve_cell_conflict():
    value, conflict = resolve_cell("qty", "1", "5", "6", "7")
    assert value == format_conflict_marker("6", "7")
    assert (conflict.key_value, conflict.column_name) == ("1", "qty")
    assert (conflict.base_val, conflict.our_val, conflict.their_val) == ("5", "6", "7")


# ---------- acceptance criterion 1: one-sided change is kept ----------

def test_change_on_one_side_is_kept():
    ours = make_table(H, ["1", "apple", "9"], ["2", "pear", "3"], ["3", "plum", "8"])
    theirs = make_table(H, ["1", "apple", "5"], ["2", "PEAR", "3"], ["3", "plum", "8"])
    result = three_way_merge(BASE, ours, theirs, "id")
    assert not result.has_conflicts
    assert rows(result) == [["1", "apple", "9"], ["2", "PEAR", "3"], ["3", "plum", "8"]]


def test_different_columns_same_row_merge_cleanly():
    ours = make_table(H, ["1", "green apple", "5"], ["2", "pear", "3"], ["3", "plum", "8"])
    theirs = make_table(H, ["1", "apple", "10"], ["2", "pear", "3"], ["3", "plum", "8"])
    result = three_way_merge(BASE, ours, theirs, "id")
    assert not result.has_conflicts
    assert rows(result)[0] == ["1", "green apple", "10"]


# ---------- acceptance criterion 2: conflicting cells are flagged ----------

def test_conflicting_cell_is_marked_and_reported():
    ours = make_table(H, ["1", "apple", "6"], ["2", "pear", "3"], ["3", "plum", "8"])
    theirs = make_table(H, ["1", "apple", "7"], ["2", "pear", "3"], ["3", "plum", "8"])
    result = three_way_merge(BASE, ours, theirs, "id")
    assert result.has_conflicts
    assert len(result.conflicts) == 1
    assert rows(result)[0][2] == format_conflict_marker("6", "7")


# ---------- acceptance criterion 3: added and deleted rows ----------

def test_rows_added_on_either_side_are_kept():
    ours = make_table(H, *[r.raw_values for r in BASE.rows], ["4", "fig", "1"])
    theirs = make_table(H, *[r.raw_values for r in BASE.rows], ["5", "kiwi", "2"])
    result = three_way_merge(BASE, ours, theirs, "id")
    assert not result.has_conflicts
    assert [r[0] for r in rows(result)] == ["1", "2", "3", "4", "5"]


def test_same_row_added_on_both_sides_differently_conflicts():
    ours = make_table(H, *[r.raw_values for r in BASE.rows], ["4", "fig", "1"])
    theirs = make_table(H, *[r.raw_values for r in BASE.rows], ["4", "fig", "2"])
    result = three_way_merge(BASE, ours, theirs, "id")
    assert [(c.key_value, c.column_name) for c in result.conflicts] == [("4", "qty")]


def test_row_deleted_on_one_side_and_unchanged_on_other_is_removed():
    ours = make_table(H, ["1", "apple", "5"], ["3", "plum", "8"])
    result = three_way_merge(BASE, ours, BASE, "id")
    assert not result.has_conflicts
    assert [r[0] for r in rows(result)] == ["1", "3"]


def test_row_deleted_on_both_sides_is_removed():
    ours = make_table(H, ["1", "apple", "5"], ["3", "plum", "8"])
    result = three_way_merge(BASE, ours, ours, "id")
    assert [r[0] for r in rows(result)] == ["1", "3"]


def test_delete_versus_edit_is_a_conflict():
    ours = make_table(H, ["1", "apple", "5"], ["3", "plum", "8"])
    theirs = make_table(H, ["1", "apple", "5"], ["2", "pear", "30"], ["3", "plum", "8"])
    result = three_way_merge(BASE, ours, theirs, "id")
    assert result.has_conflicts
    c = result.conflicts[0]
    assert (c.key_value, c.column_name, c.our_val, c.their_val) == ("2", "qty", "<deleted>", "30")
    assert "2" in [r[0] for r in rows(result)]


# ---------- columns and errors ----------

def test_column_added_on_one_side_is_kept():
    ours = make_table(H + ["note"], ["1", "apple", "5", "fresh"], ["2", "pear", "3", ""],
                      ["3", "plum", "8", ""])
    result = three_way_merge(BASE, ours, BASE, "id")
    assert not result.has_conflicts
    assert result.merged_table.headers == H + ["note"]
    assert rows(result)[0] == ["1", "apple", "5", "fresh"]


def test_column_removed_on_one_side_is_dropped():
    ours = make_table(["id", "name"], ["1", "apple"], ["2", "pear"], ["3", "plum"])
    result = three_way_merge(BASE, ours, BASE, "id")
    assert not result.has_conflicts
    assert result.merged_table.headers == ["id", "name"]
    assert rows(result) == [["1", "apple"], ["2", "pear"], ["3", "plum"]]


def test_column_removed_on_one_side_but_edited_on_other_conflicts():
    ours = make_table(["id", "name"], ["1", "apple"], ["2", "pear"], ["3", "plum"])
    theirs = make_table(H, ["1", "apple", "99"], ["2", "pear", "3"], ["3", "plum", "8"])
    result = three_way_merge(BASE, ours, theirs, "id")
    assert result.merged_table.headers == H
    assert [(c.key_value, c.column_name, c.their_val) for c in result.conflicts] == [("1", "qty", "99")]


def test_added_column_does_not_block_a_delete():
    ours = make_table(H + ["note"], ["1", "apple", "5", "x"], ["2", "pear", "3", "n"],
                      ["3", "plum", "8", "y"])
    theirs = make_table(H, ["1", "apple", "5"], ["3", "plum", "8"])
    result = three_way_merge(BASE, ours, theirs, "id")
    assert not result.has_conflicts
    assert [r[0] for r in rows(result)] == ["1", "3"]


def test_delete_versus_edit_mirror():
    ours = make_table(H, ["1", "apple", "5"], ["2", "pear", "30"], ["3", "plum", "8"])
    theirs = make_table(H, ["1", "apple", "5"], ["3", "plum", "8"])
    c = three_way_merge(BASE, ours, theirs, "id").conflicts[0]
    assert (c.our_val, c.their_val) == ("30", "<deleted>")


def test_same_row_added_identically_on_both_sides():
    extra = ["4", "fig", "1"]
    ours = make_table(H, *[r.raw_values for r in BASE.rows], extra)
    result = three_way_merge(BASE, ours, ours, "id")
    assert not result.has_conflicts
    assert [r[0] for r in rows(result)] == ["1", "2", "3", "4"]


def test_reordered_rows_follow_ours():
    ours = make_table(H, ["3", "plum", "8"], ["1", "apple", "5"], ["2", "pear", "3"])
    result = three_way_merge(BASE, ours, BASE, "id")
    assert not result.has_conflicts
    assert [r[0] for r in rows(result)] == ["3", "1", "2"]


def test_inputs_are_not_modified():
    ours = make_table(H, ["1", "apple", "6"], ["2", "pear", "3"], ["3", "plum", "8"])
    before = [dict(r.cells) for r in BASE.rows + ours.rows]
    three_way_merge(BASE, ours, BASE, "id")
    assert [dict(r.cells) for r in BASE.rows + ours.rows] == before


def test_missing_key_column_raises():
    with pytest.raises(ValueError):
        three_way_merge(BASE, BASE, BASE, "sku")


# ---------- end to end through the CLI ----------

def csv_text(*lines):
    return "\n".join(lines) + "\n"


def test_cli_merge_clean(write_file, tmp_path):
    base = write_file("base.csv", csv_text("id,qty", "1,5", "2,3"))
    ours = write_file("ours.csv", csv_text("id,qty", "1,6", "2,3"))
    theirs = write_file("theirs.csv", csv_text("id,qty", "1,5", "2,3", "3,9"))
    out = tmp_path / "merged.csv"
    assert main(["merge", str(base), str(ours), str(theirs), "--key", "id", "--output", str(out)]) == EXIT_OK
    assert out.read_text(encoding="utf-8") == csv_text("id,qty", "1,6", "2,3", "3,9")


def test_cli_merge_with_conflict(write_file, tmp_path, capsys):
    base = write_file("base.csv", csv_text("id,qty", "1,5"))
    ours = write_file("ours.csv", csv_text("id,qty", "1,6"))
    theirs = write_file("theirs.csv", csv_text("id,qty", '1,"7, maybe"'))
    out = tmp_path / "merged.csv"
    assert main(["merge", str(base), str(ours), str(theirs), "--key", "id", "--output", str(out)]) == EXIT_CONFLICTS
    assert "1 conflict" in capsys.readouterr().out
    assert read_csv(out).rows[0].cells["qty"] == format_conflict_marker("6", "7, maybe")


def test_cli_merge_bad_key_is_an_error(write_file, tmp_path, capsys):
    base = write_file("base.csv", csv_text("id,qty", "1,5"))
    out = tmp_path / "merged.csv"
    assert main(["merge", str(base), str(base), str(base), "--key", "sku", "--output", str(out)]) == EXIT_ERROR
    assert "error:" in capsys.readouterr().err
    assert not out.exists()
