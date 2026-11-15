"""Tests for the column filter (Card 7): differ.filter_columns and the --columns option."""
from conftest import make_table
from src.cli import EXIT_ERROR, EXIT_OK, main
from src.differ import compute_diff, filter_columns

H = ["id", "name", "city"]
EXAMPLE = "testing/test_cases/test_case_example"


# ---------- filter_columns ----------

def test_keeps_only_selected_columns_and_the_key():
    table = make_table(H, ["1", "Ana", "NY"])
    filtered = filter_columns(table, ["city"], "id")
    assert filtered.headers == ["id", "city"]
    assert filtered.rows[0].cells == {"id": "1", "city": "NY"}
    assert filtered.rows[0].raw_values == ["1", "NY"]


def test_key_is_kept_even_when_not_selected():
    table = make_table(H, ["1", "Ana", "NY"])
    assert "id" in filter_columns(table, ["name"], "id").headers


def test_row_indexes_and_original_table_are_untouched():
    table = make_table(H, ["1", "Ana", "NY"], ["2", "Bo", "LA"])
    filtered = filter_columns(table, ["name"], "id")
    assert [r.row_index for r in filtered.rows] == [0, 1]
    assert table.headers == H
    assert table.rows[0].cells == {"id": "1", "name": "Ana", "city": "NY"}


def test_change_in_unselected_column_is_not_reported():
    a = make_table(H, ["1", "Ana", "NY"])
    b = make_table(H, ["1", "Ana", "LA"])
    diff = compute_diff(filter_columns(a, ["name"], "id"), filter_columns(b, ["name"], "id"), key_col="id")
    assert diff.changes == []


def test_change_in_selected_column_is_reported_and_ids_still_match():
    a = make_table(H, ["1", "Ana", "NY"], ["2", "Bo", "LA"])
    b = make_table(H, ["2", "Bo", "SF"], ["1", "Ana", "NY"])
    diff = compute_diff(filter_columns(a, ["city"], "id"), filter_columns(b, ["city"], "id"), key_col="id")
    modified = [c for c in diff.changes if c.cell_changes]
    assert [c.key_value for c in modified] == ["2"]
    assert modified[0].cell_changes[0].column_value == "city"


# ---------- command line ----------

def run(capsys, *extra):
    code = main(["diff", f"{EXAMPLE}/base.csv", f"{EXAMPLE}/modified.csv", "--key", "id", *extra])
    out, err = capsys.readouterr()
    return code, out, err


def test_cli_columns_limits_the_report(capsys):
    code, out, _ = run(capsys, "--columns", "salary", "--no-color")
    assert code == EXIT_OK
    assert "salary: '91000' -> '95000'" in out
    assert "department" not in out
    assert "MOVED AND MODIFIED" not in out


def test_cli_accepts_several_columns(capsys):
    code, out, _ = run(capsys, "--columns", "salary,department", "--no-color")
    assert code == EXIT_OK
    assert "salary:" in out and "department:" in out


def test_cli_unknown_column_gives_clear_error(capsys):
    code, out, err = run(capsys, "--columns", "salary,nope")
    assert code == EXIT_ERROR
    assert "nope" in err
    assert out == ""


def test_cli_empty_columns_gives_clear_error(capsys):
    code, _, err = run(capsys, "--columns", ",")
    assert code == EXIT_ERROR
    assert "at least one column" in err
