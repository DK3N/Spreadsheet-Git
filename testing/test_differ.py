
"""Tests for src.differ (Card #1101): compute_diff / diff_cells."""

import csv
import dataclasses
import json
import random
from collections import defaultdict, deque
from pathlib import Path
from unittest.mock import patch

import pytest

from src.differ import compute_diff, diff_cells
from src.matcher import match_rows as real_match_rows
from src.models import ChangeType, Row, Table

EXAMPLE_DIR = Path(__file__).parent / "test_cases" / "test_case_example"


# ---------- helpers ----------

def make_table(headers, rows):
    return Table(
        headers=headers,
        rows=[Row(row_index=i, cells=dict(zip(headers, vals)), raw_values=list(vals))
              for i, vals in enumerate(rows)],
    )


def fake_match_rows(table_a, table_b, key_col=None, threshold=0.7):
    def key(row):
        return row.row_index if key_col is None else row.cells[key_col]

    waiting_in_b = defaultdict(deque)
    for row in table_b.rows:
        waiting_in_b[key(row)].append(row)

    pairs, deleted = [], []
    for row in table_a.rows:
        if waiting_in_b[key(row)]:
            pairs.append((row, waiting_in_b[key(row)].popleft()))
        else:
            deleted.append(row)
    inserted = [row for rows in waiting_in_b.values() for row in rows]
    return pairs, deleted, inserted


@pytest.fixture(autouse=True)
def fake_matcher():
    with patch("src.differ.match_rows", side_effect=fake_match_rows) as mock:
        yield mock


def use_matcher_result(mock, pairs=(), deleted=(), inserted=()):
    mock.side_effect = None
    mock.return_value = (list(pairs), list(deleted), list(inserted))


def kinds(result):
    return [(c.change_type, c.key_value) for c in result.changes]


def cell_tuples(cell_changes):
    return [(c.column_value, c.old_value, c.new_value) for c in cell_changes]


def as_plain_dict(row_change):
    plain = dataclasses.asdict(row_change)
    plain["change_type"] = row_change.change_type.value
    return plain


def read_example_csv(name):
    with open(EXAMPLE_DIR / name, newline="", encoding="utf-8") as f:
        headers, *rows = list(csv.reader(f))
    return make_table(headers, rows)


def longest_increasing_length(values):
    best = [1] * len(values)
    for i, val in enumerate(values):
        for j in range(i):
            if values[j] < val:
                best[i] = max(best[i], best[j] + 1)
    return max(best, default=0)


H = ["id", "name", "qty"]
A, B, C, D = ["1", "apple", "5"], ["2", "pear", "3"], ["3", "plum", "8"], ["4", "kiwi", "1"]
BASE = [A, B, C, D]
FIG = ["5", "fig", "2"]


def diff_against_base(new_rows):
    return compute_diff(make_table(H, BASE), make_table(H, new_rows), key_col="id")


# ---------- diff_cells ----------

@pytest.mark.parametrize(
    "cells_a, cells_b, headers, expected",
    [
        pytest.param(
            {"id": "1", "qty": "5"}, {"id": "1", "qty": "5"}, ["id", "qty"], [],
            id="identical",
        ),
        pytest.param(
            {"id": "1", "name": "apple", "qty": "5"}, {"id": "1", "name": "apple", "qty": "9"}, H,
            [("qty", "5", "9")],
            id="only_changed_columns",
        ),
        pytest.param(
            {"id": "1", "qty": "5"}, {"id": "2", "qty": "9"}, ["qty", "id"],
            [("qty", "5", "9"), ("id", "1", "2")],
            id="follows_headers_order",
        ),
        pytest.param(
            {"id": "1"}, {"id": "1", "note": "hi"}, ["id", "note"], [("note", "", "hi")],
            id="column_missing_from_old",
        ),
        pytest.param(
            {"id": "1", "note": "hi"}, {"id": "1"}, ["id", "note"], [("note", "hi", "")],
            id="column_missing_from_new",
        ),
        pytest.param(
            {"id": "1", "note": ""}, {"id": "1"}, ["id", "note"], [],
            id="empty_equals_missing",
        ),
        pytest.param({"id": "1"}, {"id": "1"}, ["id", "note"], [], id="missing_from_both"),
        pytest.param({"v": "a"}, {"v": " a"}, ["v"], [("v", "a", " a")], id="whitespace_counts"),
        pytest.param({"v": "a"}, {"v": "A"}, ["v"], [("v", "a", "A")], id="case_counts"),
        pytest.param({"v": "1"}, {"v": "1.0"}, ["v"], [("v", "1", "1.0")], id="compared_as_text"),
        pytest.param({"id": "1", "v": "a"}, {"id": "1", "v": "b"}, ["id"], [], id="ignores_other_columns"),
    ],
)
def test_diff_cells(cells_a, cells_b, headers, expected):
    assert cell_tuples(diff_cells(Row(0, cells_a, []), Row(0, cells_b, []), headers)) == expected


# ---------- classification ----------

@pytest.mark.parametrize(
    "new_rows, expected",
    [
        pytest.param(BASE, [], id="identical_reports_nothing"),
        pytest.param(BASE + [FIG], [(ChangeType.INSERTED, "5")], id="insert_at_end"),
        pytest.param([FIG] + BASE, [(ChangeType.INSERTED, "5")], id="insert_at_start"),
        pytest.param([A, B, FIG, C, D], [(ChangeType.INSERTED, "5")], id="insert_in_middle"),
        pytest.param([B, C, D], [(ChangeType.DELETED, "1")], id="delete_first"),
        pytest.param([A, C, D], [(ChangeType.DELETED, "2")], id="delete_middle"),
        pytest.param([A, B, C], [(ChangeType.DELETED, "4")], id="delete_last"),
        pytest.param(
            [A, ["2", "pear", "30"], C, D], [(ChangeType.MODIFIED, "2")],
            id="modified",
        ),
        pytest.param([A, C, D, B], [(ChangeType.MOVED, "2")], id="moved_down"),
        pytest.param([D, A, B, C], [(ChangeType.MOVED, "4")], id="moved_up"),
        pytest.param(
            [A, C, D, ["2", "pear", "99"]], [(ChangeType.MOVED_AND_MODIFIED, "2")],
            id="moved_and_modified",
        ),
        pytest.param(
            [["1", "apple", "6"], C, D, FIG],
            [(ChangeType.MODIFIED, "1"), (ChangeType.INSERTED, "5"), (ChangeType.DELETED, "2")],
            id="insert_delete_and_modify_together",
        ),
    ],
)
def test_classification(new_rows, expected):
    assert kinds(diff_against_base(new_rows)) == expected


@pytest.mark.parametrize(
    "new_rows, kind, old_index, new_index",
    [
        pytest.param(BASE + [FIG], ChangeType.INSERTED, None, 4, id="inserted"),
        pytest.param([A, C, D], ChangeType.DELETED, 1, None, id="deleted"),
        pytest.param([A, ["2", "pear", "30"], C, D], ChangeType.MODIFIED, 1, 1, id="modified"),
        pytest.param([A, C, D, B], ChangeType.MOVED, 1, 3, id="moved"),
        pytest.param([A, C, D, ["2", "pear", "99"]], ChangeType.MOVED_AND_MODIFIED, 1, 3, id="moved_and_modified"),
    ],
)
def test_indexes_for_each_change_type(new_rows, kind, old_index, new_index):
    change = diff_against_base(new_rows).changes[0]
    assert (change.change_type, change.old_index, change.new_index) == (kind, old_index, new_index)


@pytest.mark.parametrize(
    "new_rows, expected_cells",
    [
        pytest.param(BASE + [FIG], [], id="inserted_has_none"),
        pytest.param([A, C, D], [], id="deleted_has_none"),
        pytest.param([A, C, D, B], [], id="moved_has_none"),
        pytest.param([A, ["2", "pear", "30"], C, D], [("qty", "3", "30")], id="modified"),
        pytest.param([A, C, D, ["2", "pip", "9"]], [("name", "pear", "pip"), ("qty", "3", "9")], id="moved_and_modified"),
    ],
)
def test_cell_changes_for_each_change_type(new_rows, expected_cells):
    assert cell_tuples(diff_against_base(new_rows).changes[0].cell_changes) == expected_cells


@pytest.mark.parametrize(
    "new_rows, expected_row",
    [
        pytest.param(BASE + [FIG], FIG, id="inserted_has_new_row"),
        pytest.param([A, C, D], B, id="deleted_has_old_row"),
        pytest.param([A, ["2", "pear", "30"], C, D], ["2", "pear", "30"], id="modified_has_new_version"),
    ],
)
def test_raw_row(new_rows, expected_row):
    assert diff_against_base(new_rows).changes[0].raw_row == dict(zip(H, expected_row))


def test_raw_row_is_a_copy():
    old = make_table(H, BASE)
    new = make_table(H, BASE + [FIG])
    compute_diff(old, new, key_col="id").changes[0].raw_row["qty"] = "changed"
    assert new.rows[4].cells["qty"] == "2"


# ---------- move detection ----------

@pytest.mark.parametrize(
    "new_rows, expected",
    [
        pytest.param(BASE[1:], [(ChangeType.DELETED, "1")], id="delete_first_row_shifts_all_up"),
        pytest.param([FIG] + BASE, [(ChangeType.INSERTED, "5")], id="insert_first_row_shifts_all_down"),
        pytest.param(
            [FIG, ["6", "lime", "1"], B, C, D],
            [(ChangeType.INSERTED, "5"), (ChangeType.INSERTED, "6"), (ChangeType.DELETED, "1")],
            id="insert_and_delete_shift_in_opposite_ways",
        ),
    ],
)
def test_shifted_rows_are_not_moved(new_rows, expected):
    assert kinds(diff_against_base(new_rows)) == expected


@pytest.mark.parametrize(
    "new_rows, moved_count",
    [
        pytest.param([B, A, C, D], 1, id="adjacent_swap"),
        pytest.param([D, B, C, A], 2, id="swap_ends"),
        pytest.param([C, D, A, B], 2, id="two_blocks_swapped"),
        pytest.param([D, C, B, A], 3, id="reversed"),
    ],
)
def test_fewest_possible_rows_are_moved(new_rows, moved_count):
    changes = diff_against_base(new_rows).changes
    assert len(changes) == moved_count
    assert all(c.change_type == ChangeType.MOVED for c in changes)


def test_tied_swap_gives_a_fixed_answer():
    assert kinds(diff_against_base([B, A, C, D])) == [(ChangeType.MOVED, "2")]


@pytest.mark.parametrize("seed", range(25))
def test_moved_count_matches_reference_on_random_shuffles(seed):
    rng = random.Random(seed)
    n = rng.randint(0, 60)
    old_order = list(range(n))
    new_order = rng.sample(old_order, n)
    rows = [[str(i), f"row{i}"] for i in old_order]

    result = compute_diff(
        make_table(["id", "v"], rows),
        make_table(["id", "v"], [rows[i] for i in new_order]),
        key_col="id",
    )

    assert len(result.changes) == n - longest_increasing_length(new_order)
    stayed = [i for i in new_order if str(i) not in {c.key_value for c in result.changes}]
    assert stayed == sorted(stayed)


def test_move_detection_uses_row_index_not_position_in_table():
    def table(*keys_and_indexes):
        return Table(["id"], [Row(i, {"id": key}, [key]) for key, i in keys_and_indexes])

    old = table(("a", 10), ("b", 20), ("c", 30))
    gaps_only = table(("a", 5), ("b", 99), ("c", 100))
    assert compute_diff(old, gaps_only, key_col="id").changes == []

    a_moved_to_end = table(("b", 5), ("c", 99), ("a", 100))
    changes = compute_diff(old, a_moved_to_end, key_col="id").changes
    assert [(c.change_type, c.old_index, c.new_index) for c in changes] == [(ChangeType.MOVED, 10, 100)]


# ---------- empty tables ----------

EMPTY_FILE = ([], [])
HEADER_ONLY = (H, [])
WITH_ROWS = (H, [A, B])


@pytest.mark.parametrize(
    "old, new, expected",
    [
        pytest.param(EMPTY_FILE, EMPTY_FILE, [], id="both_empty_files"),
        pytest.param(HEADER_ONLY, HEADER_ONLY, [], id="both_header_only"),
        pytest.param(EMPTY_FILE, HEADER_ONLY, [], id="empty_file_vs_header_only"),
        pytest.param(HEADER_ONLY, EMPTY_FILE, [], id="header_only_vs_empty_file"),
        pytest.param(
            EMPTY_FILE, WITH_ROWS, [(ChangeType.INSERTED, "1"), (ChangeType.INSERTED, "2")],
            id="old_is_empty_file",
        ),
        pytest.param(
            HEADER_ONLY, WITH_ROWS, [(ChangeType.INSERTED, "1"), (ChangeType.INSERTED, "2")],
            id="old_is_header_only",
        ),
        pytest.param(
            WITH_ROWS, EMPTY_FILE, [(ChangeType.DELETED, "1"), (ChangeType.DELETED, "2")],
            id="new_is_empty_file",
        ),
        pytest.param(
            WITH_ROWS, HEADER_ONLY, [(ChangeType.DELETED, "1"), (ChangeType.DELETED, "2")],
            id="new_is_header_only",
        ),
    ],
)
def test_empty_tables(old, new, expected):
    assert kinds(compute_diff(make_table(*old), make_table(*new), key_col="id")) == expected


# ---------- column changes ----------

@pytest.mark.parametrize(
    "old_headers, old_rows, new_headers, new_rows, expected",
    [
        pytest.param(
            ["id", "v"], [["1", "a"]], ["id", "v", "note"], [["1", "a", "hi"]],
            [("1", [("note", "", "hi")])],
            id="column_added_with_value",
        ),
        pytest.param(
            ["id", "v"], [["1", "a"]], ["id", "v", "note"], [["1", "a", ""]], [],
            id="column_added_blank_is_not_a_change",
        ),
        pytest.param(
            ["id", "v", "note"], [["1", "a", "hi"]], ["id", "v"], [["1", "a"]],
            [("1", [("note", "hi", "")])],
            id="column_removed_with_value",
        ),
        pytest.param(
            ["id", "v", "note"], [["1", "a", ""]], ["id", "v"], [["1", "a"]], [],
            id="column_removed_blank_is_not_a_change",
        ),
        pytest.param(
            ["id", "v"], [["1", "a"]], ["id", "value"], [["1", "a"]],
            [("1", [("v", "a", ""), ("value", "", "a")])],
            id="column_renamed_looks_like_drop_plus_add",
        ),
        pytest.param(
            ["id", "x", "y"], [["1", "a", "b"]], ["y", "id", "x"], [["b", "1", "a"]], [],
            id="pure_column_reorder_is_not_reported",
        ),
        pytest.param(
            ["id", "x", "y"], [["1", "a", "b"]], ["y", "x", "id"], [["B", "A", "1"]],
            [("1", [("x", "a", "A"), ("y", "b", "B")])],
            id="reorder_plus_edit_uses_old_column_order",
        ),
        pytest.param(
            ["id", "x"], [["1", "a"]], ["n", "id", "x"], [["z", "1", "A"]],
            [("1", [("x", "a", "A"), ("n", "", "z")])],
            id="new_only_columns_come_after_old_columns",
        ),
    ],
)
def test_column_changes(old_headers, old_rows, new_headers, new_rows, expected):
    result = compute_diff(
        make_table(old_headers, old_rows), make_table(new_headers, new_rows), key_col="id"
    )
    assert [(c.key_value, cell_tuples(c.cell_changes)) for c in result.changes] == expected
    assert all(c.change_type == ChangeType.MODIFIED for c in result.changes)


def test_repeated_header_name_reports_one_cell_change():
    headers = ["id", "v", "v"]
    old = Table(headers, [Row(0, {"id": "1", "v": "a"}, ["1", "a", "a"])])
    new = Table(headers, [Row(0, {"id": "1", "v": "b"}, ["1", "b", "b"])])
    change = compute_diff(old, new, key_col="id").changes[0]
    assert cell_tuples(change.cell_changes) == [("v", "a", "b")]


def test_short_row_missing_cell_equals_empty_cell():
    old = Table(["id", "v"], [Row(0, {"id": "1", "v": ""}, ["1", ""])])
    new = Table(["id", "v"], [Row(0, {"id": "1"}, ["1"])])
    assert compute_diff(old, new, key_col="id").changes == []


# ---------- key_col ----------

def test_key_col_defaults_to_none_and_is_passed_to_matcher(fake_matcher):
    old, new = make_table(H, BASE), make_table(H, BASE)
    compute_diff(old, new)
    fake_matcher.assert_called_once_with(old, new, key_col=None)


def test_no_key_col_reports_row_index_as_key():
    old = make_table(H, [A, B, C])
    new = make_table(H, [A, ["2", "pear", "30"], C, FIG])
    assert kinds(compute_diff(old, new)) == [(ChangeType.MODIFIED, 1), (ChangeType.INSERTED, 3)]


def test_no_key_col_deleted_row_reports_old_index_as_key():
    assert kinds(compute_diff(make_table(H, [A, B]), make_table(H, [A]))) == [(ChangeType.DELETED, 1)]


def test_row_missing_its_key_cell_falls_back_to_row_index(fake_matcher):
    old_row = Row(7, {"name": "apple"}, ["apple"])
    use_matcher_result(fake_matcher, deleted=[old_row])
    result = compute_diff(Table(H, [old_row]), make_table(H, []), key_col="id")
    assert kinds(result) == [(ChangeType.DELETED, 7)]


@pytest.mark.parametrize(
    "old_headers, new_headers",
    [
        pytest.param(["name"], H, id="missing_from_old"),
        pytest.param(H, ["name"], id="missing_from_new"),
        pytest.param(["name"], ["name"], id="missing_from_both"),
    ],
)
def test_key_col_not_in_headers_raises_before_matching(fake_matcher, old_headers, new_headers):
    old = make_table(old_headers, [["x"] * len(old_headers)])
    new = make_table(new_headers, [["x"] * len(new_headers)])
    with pytest.raises(ValueError, match="key column 'id' not found"):
        compute_diff(old, new, key_col="id")
    fake_matcher.assert_not_called()


# ---------- duplicate keys and the match_rows contract ----------

def test_duplicate_keys_paired_one_to_one_are_diffed_normally():
    old = make_table(H, [["1", "apple", "5"], ["1", "apricot", "6"]])
    new = make_table(H, [["1", "apple", "5"], ["1", "apricot", "7"]])
    result = compute_diff(old, new, key_col="id")
    assert kinds(result) == [(ChangeType.MODIFIED, "1")]
    assert result.changes[0].new_index == 1


@pytest.mark.parametrize(
    "old_rows, new_rows, expected",
    [
        pytest.param(
            [A, ["1", "apricot", "6"]], [A],
            [(ChangeType.DELETED, "1", 1, None)],
            id="extra_duplicate_in_old",
        ),
        pytest.param(
            [A], [A, ["1", "apricot", "6"]],
            [(ChangeType.INSERTED, "1", None, 1)],
            id="extra_duplicate_in_new",
        ),
        pytest.param(
            [A, A], [FIG, FIG],
            [(ChangeType.INSERTED, "5", None, 0), (ChangeType.INSERTED, "5", None, 1),
             (ChangeType.DELETED, "1", 0, None), (ChangeType.DELETED, "1", 1, None)],
            id="same_key_twice_is_told_apart_by_index",
        ),
    ],
)
def test_duplicate_keys_with_extras(old_rows, new_rows, expected):
    result = compute_diff(make_table(H, old_rows), make_table(H, new_rows), key_col="id")
    assert [(c.change_type, c.key_value, c.old_index, c.new_index) for c in result.changes] == expected


def _two_old_one_new():
    return make_table(H, [A, ["1", "apricot", "6"]]), make_table(H, [A])


def _one_old_two_new():
    return make_table(H, [A]), make_table(H, [A, ["1", "apricot", "6"]])


@pytest.mark.parametrize(
    "tables, matcher_result, table_named",
    [
        pytest.param(
            _two_old_one_new,
            lambda a, b: ([(a.rows[0], b.rows[0]), (a.rows[1], b.rows[0])], [], []),
            "table_b",
            id="two_old_rows_paired_to_one_new_row",
        ),
        pytest.param(
            _one_old_two_new,
            lambda a, b: ([(a.rows[0], b.rows[0]), (a.rows[0], b.rows[1])], [], []),
            "table_a",
            id="one_old_row_paired_to_two_new_rows",
        ),
        pytest.param(
            _two_old_one_new,
            lambda a, b: ([(a.rows[0], b.rows[0])], [], []),
            "table_a",
            id="old_row_lost",
        ),
        pytest.param(
            _one_old_two_new,
            lambda a, b: ([(a.rows[0], b.rows[0])], [], []),
            "table_b",
            id="new_row_lost",
        ),
        pytest.param(
            _two_old_one_new,
            lambda a, b: ([(a.rows[0], b.rows[0])], [a.rows[0], a.rows[1]], []),
            "table_a",
            id="row_both_paired_and_deleted",
        ),
        pytest.param(
            _one_old_two_new,
            lambda a, b: ([], [], []),
            "table_a",
            id="stub_result_for_non_empty_tables",
        ),
    ],
)
def test_matcher_breaking_the_contract_raises(fake_matcher, tables, matcher_result, table_named):
    old, new = tables()
    use_matcher_result(fake_matcher, *matcher_result(old, new))
    with pytest.raises(ValueError, match=f"each row of {table_named} exactly once"):
        compute_diff(old, new, key_col="id")


# ---------- output order ----------

def test_changes_in_new_order_then_deletions_in_old_order():
    new_rows = [["5", "fig", "2"], ["2", "pear", "30"], ["6", "lime", "1"]]
    old = make_table(H, BASE)
    result = compute_diff(old, make_table(H, new_rows), key_col="id")
    assert kinds(result) == [
        (ChangeType.INSERTED, "5"),
        (ChangeType.MODIFIED, "2"),
        (ChangeType.INSERTED, "6"),
        (ChangeType.DELETED, "1"),
        (ChangeType.DELETED, "3"),
        (ChangeType.DELETED, "4"),
    ]


def test_order_does_not_depend_on_order_returned_by_matcher(fake_matcher):
    old = make_table(H, [A, B, C, D])
    new = make_table(H, [["1", "apple", "6"], ["3", "plum", "9"], FIG])
    use_matcher_result(
        fake_matcher,
        pairs=[(old.rows[2], new.rows[1]), (old.rows[0], new.rows[0])],
        deleted=[old.rows[3], old.rows[1]],
        inserted=[new.rows[2]],
    )
    assert kinds(compute_diff(old, new, key_col="id")) == [
        (ChangeType.MODIFIED, "1"),
        (ChangeType.MODIFIED, "3"),
        (ChangeType.INSERTED, "5"),
        (ChangeType.DELETED, "2"),
        (ChangeType.DELETED, "4"),
    ]


# ---------- example fixture ----------

def assert_matches_example(key_col="id"):
    expected = json.loads((EXAMPLE_DIR / "expected_diff.json").read_text(encoding="utf-8"))
    result = compute_diff(read_example_csv("base.csv"), read_example_csv("modified.csv"), key_col)
    assert expected["key_col"] == key_col
    assert [as_plain_dict(c) for c in result.changes] == expected["changes"]


def test_example_fixture():
    assert_matches_example()


# ---------- integration with the real matcher ----------

def _matcher_is_stub():
    probe = make_table(["id"], [["1"]])
    return real_match_rows(probe, probe, "id") == ([], [], [])


real_matcher_only = pytest.mark.skipif(
    _matcher_is_stub(), reason="matcher.match_rows is still a stub (card #1094)"
)


@real_matcher_only
class TestWithRealMatcher:
    @pytest.fixture(autouse=True)
    def fake_matcher(self):
        with patch("src.differ.match_rows", real_match_rows):
            yield

    @pytest.mark.parametrize(
        "new_rows, expected",
        [
            pytest.param(BASE, [], id="identical"),
            pytest.param([FIG] + BASE, [(ChangeType.INSERTED, "5")], id="inserted_shifts_rows"),
            pytest.param(BASE[1:], [(ChangeType.DELETED, "1")], id="deleted_shifts_rows"),
            pytest.param([A, ["2", "pear", "30"], C, D], [(ChangeType.MODIFIED, "2")], id="modified"),
            pytest.param([A, C, D, B], [(ChangeType.MOVED, "2")], id="moved"),
            pytest.param(
                [A, C, D, ["2", "pear", "99"]], [(ChangeType.MOVED_AND_MODIFIED, "2")],
                id="moved_and_modified",
            ),
        ],
    )
    def test_each_change_type_with_key(self, new_rows, expected):
        assert kinds(diff_against_base(new_rows)) == expected

    @pytest.mark.parametrize(
        "old, new, expected",
        [
            pytest.param(HEADER_ONLY, HEADER_ONLY, [], id="both_header_only"),
            pytest.param(HEADER_ONLY, WITH_ROWS, [ChangeType.INSERTED] * 2, id="old_header_only"),
            pytest.param(WITH_ROWS, HEADER_ONLY, [ChangeType.DELETED] * 2, id="new_header_only"),
        ],
    )
    def test_header_only_tables(self, old, new, expected):
        result = compute_diff(make_table(*old), make_table(*new), key_col="id")
        assert [c.change_type for c in result.changes] == expected

    def test_duplicate_keys_are_rejected_by_the_matcher(self):
        old = make_table(H, [A, ["1", "apricot", "6"], B])
        with pytest.raises(ValueError, match="duplicate"):
            compute_diff(old, make_table(H, BASE), key_col="id")

    def test_no_key_identical_tables_report_nothing(self):
        assert compute_diff(make_table(H, BASE), make_table(H, BASE)).changes == []

    def test_no_key_finds_a_move_by_content(self):
        result = compute_diff(make_table(H, BASE), make_table(H, [A, C, D, B]))
        assert [(c.change_type, c.old_index, c.new_index) for c in result.changes] == [
            (ChangeType.MOVED, 1, 3)
        ]

    def test_no_key_finds_a_small_edit_by_similarity(self):
        headers = [f"c{i}" for i in range(10)]
        row = [f"v{i}" for i in range(10)]
        edited = row[:-1] + ["changed"]
        other = [f"other{i}" for i in range(10)]
        result = compute_diff(make_table(headers, [other, row]), make_table(headers, [other, edited]))
        assert [(c.change_type, c.old_index, c.new_index) for c in result.changes] == [
            (ChangeType.MODIFIED, 1, 1)
        ]
        assert cell_tuples(result.changes[0].cell_changes) == [("c9", "v9", "changed")]

    def test_example_fixture(self):
        assert_matches_example()


# ---------- Sprint 2: Column Change Detection ----------

def test_added_column():
    old = make_table(["id", "name"], [["1", "John"]])
    new = make_table(["id", "name", "age"], [["1", "John", "25"]])

    result = compute_diff(old, new, key_col="id")

    assert result.added_columns == ["age"]
    assert result.removed_columns == []
    assert result.columns_reordered is False


def test_removed_column():
    old = make_table(["id", "name", "age"], [["1", "John", "25"]])
    new = make_table(["id", "name"], [["1", "John"]])

    result = compute_diff(old, new, key_col="id")

    assert result.added_columns == []
    assert result.removed_columns == ["age"]
    assert result.columns_reordered is False


def test_reordered_columns():
    old = make_table(["id", "name", "age"], [["1", "John", "25"]])
    new = make_table(["age", "id", "name"], [["25", "1", "John"]])

    result = compute_diff(old, new, key_col="id")

    assert result.added_columns == []
    assert result.removed_columns == []
    assert result.columns_reordered is True
    assert result.changes == []


def test_added_blank_column():
    old = make_table(["id", "name"], [["1", "John"]])
    new = make_table(["id", "name", "email"], [["1", "John", ""]])

    result = compute_diff(old, new, key_col="id")

    assert result.added_columns == ["email"]
    assert result.changes == []


def test_removed_blank_column():
    old = make_table(["id", "name", "email"], [["1", "John", ""]])
    new = make_table(["id", "name"], [["1", "John"]])

    result = compute_diff(old, new, key_col="id")

    assert result.removed_columns == ["email"]
    assert result.changes == []


def test_no_column_changes():
    old = make_table(["id", "name"], [["1", "John"]])
    new = make_table(["id", "name"], [["1", "John"]])

    result = compute_diff(old, new, key_col="id")

    assert result.added_columns == []
    assert result.removed_columns == []
    assert result.columns_reordered is False
    assert result.changes == []


def test_added_removed_and_reordered_columns():
    old = make_table(
        ["id", "name", "phone"],
        [["1", "John", "123"]]
    )
    new = make_table(
        ["name", "id", "email"],
        [["John", "1", "john@email.com"]]
    )

    result = compute_diff(old, new, key_col="id")

    assert result.added_columns == ["email"]
    assert result.removed_columns == ["phone"]
    assert result.columns_reordered is True


def test_reordered_columns_with_real_matcher():
    old = make_table(["id", "name", "age"], [["1", "John", "25"]])
    new = make_table(["age", "id", "name"], [["25", "1", "John"]])

    with patch("src.differ.match_rows", real_match_rows):
        result = compute_diff(old, new, key_col="id")

    assert result.columns_reordered is True
    assert result.changes == []


def test_column_changes_terminal_output():
    from src.printer import render_diff_terminal

    old = make_table(["id", "name"], [["1", "John"]])
    new = make_table(["id", "name", "email"], [["1", "John", ""]])

    result = compute_diff(old, new, key_col="id")
    output = render_diff_terminal(result, use_color=False)

    assert "Column Changes:" in output
    assert "+ Column added: email" in output
    assert "No row changes detected." in output
    assert "No differences found." not in output
