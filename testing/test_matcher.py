"""Tests for src.matcher (Card 2): match_rows / compute_row_similarity."""
import pytest

from conftest import make_table
from src.matcher import compute_row_similarity, match_rows

H = ["id", "name", "city"]


def keys(rows, col="id"):
    return [r.cells[col] for r in rows]


# ---------- key-based matching ----------

def test_matches_same_order_by_key():
    a = make_table(H, ["1", "Ana", "NY"], ["2", "Bo", "LA"])
    b = make_table(H, ["1", "Ana", "NY"], ["2", "Bo", "LA"])
    pairs, deleted, inserted = match_rows(a, b, key_col="id")
    assert [(x.cells["id"], y.cells["id"]) for x, y in pairs] == [("1", "1"), ("2", "2")]
    assert deleted == [] and inserted == []


def test_reordered_rows_still_match():
    a = make_table(H, ["1", "Ana", "NY"], ["2", "Bo", "LA"], ["3", "Cy", "SF"])
    b = make_table(H, ["3", "Cy", "SF"], ["1", "Ana", "NY"], ["2", "Bo", "LA"])
    pairs, deleted, inserted = match_rows(a, b, key_col="id")
    assert all(x.cells["id"] == y.cells["id"] for x, y in pairs)
    assert keys([x for x, _ in pairs]) == ["1", "2", "3"]  # ordered by table A
    assert deleted == [] and inserted == []


def test_matched_row_with_changed_values_is_still_matched():
    a = make_table(H, ["1", "Ana", "NY"])
    b = make_table(H, ["1", "Anna", "LA"])
    pairs, deleted, inserted = match_rows(a, b, key_col="id")
    assert len(pairs) == 1 and deleted == [] and inserted == []


def test_row_only_in_a_is_deleted_and_only_in_b_is_inserted():
    a = make_table(H, ["1", "Ana", "NY"], ["2", "Bo", "LA"])
    b = make_table(H, ["2", "Bo", "LA"], ["3", "Cy", "SF"])
    pairs, deleted, inserted = match_rows(a, b, key_col="id")
    assert keys([x for x, _ in pairs]) == ["2"]
    assert keys(deleted) == ["1"]
    assert keys(inserted) == ["3"]


def test_completely_different_keys():
    a = make_table(H, ["1", "Ana", "NY"])
    b = make_table(H, ["2", "Bo", "LA"])
    pairs, deleted, inserted = match_rows(a, b, key_col="id")
    assert pairs == [] and keys(deleted) == ["1"] and keys(inserted) == ["2"]


def test_empty_tables():
    a, b = make_table(H), make_table(H)
    assert match_rows(a, b, key_col="id") == ([], [], [])


def test_empty_old_table_all_inserted():
    pairs, deleted, inserted = match_rows(make_table(H), make_table(H, ["1", "A", "B"]), key_col="id")
    assert pairs == [] and deleted == [] and keys(inserted) == ["1"]


def test_empty_new_table_all_deleted():
    pairs, deleted, inserted = match_rows(make_table(H, ["1", "A", "B"]), make_table(H), key_col="id")
    assert pairs == [] and inserted == [] and keys(deleted) == ["1"]


def test_key_comparison_is_exact_string_match():
    a = make_table(H, ["1", "Ana", "NY"])
    b = make_table(H, ["01", "Ana", "NY"])
    pairs, deleted, inserted = match_rows(a, b, key_col="id")
    assert pairs == [] and len(deleted) == 1 and len(inserted) == 1


def test_key_column_other_than_first():
    a = make_table(H, ["1", "Ana", "NY"], ["2", "Bo", "LA"])
    b = make_table(H, ["9", "Bo", "LA"], ["8", "Ana", "NY"])
    pairs, _, _ = match_rows(a, b, key_col="name")
    assert [(x.cells["id"], y.cells["id"]) for x, y in pairs] == [("1", "8"), ("2", "9")]


# ---------- key-based errors (Card 2 acceptance criteria) ----------

def test_missing_key_column_raises():
    a = make_table(H, ["1", "A", "B"])
    b = make_table(["x", "y"], ["1", "2"])
    with pytest.raises(ValueError, match="'id'"):
        match_rows(a, b, key_col="id")


def test_key_column_missing_from_old_table_only_raises():
    a = make_table(["x", "name"], ["1", "A"])
    b = make_table(H, ["1", "A", "B"])
    with pytest.raises(ValueError):
        match_rows(a, b, key_col="id")


def test_duplicate_key_in_old_table_raises():
    a = make_table(H, ["1", "Ana", "NY"], ["1", "Dup", "LA"])
    b = make_table(H, ["1", "Ana", "NY"])
    with pytest.raises(ValueError, match="duplicate"):
        match_rows(a, b, key_col="id")


def test_duplicate_key_in_new_table_raises():
    a = make_table(H, ["1", "Ana", "NY"])
    b = make_table(H, ["1", "Ana", "NY"], ["1", "Dup", "LA"])
    with pytest.raises(ValueError, match="duplicate"):
        match_rows(a, b, key_col="id")


@pytest.mark.parametrize("blank", ["", "   "])
def test_blank_key_value_raises_with_row_index(blank):
    a = make_table(H, ["1", "Ana", "NY"], [blank, "Bo", "LA"])
    b = make_table(H, ["1", "Ana", "NY"])
    with pytest.raises(ValueError, match="blank value at row 1"):
        match_rows(a, b, key_col="id")


def test_blank_key_value_in_new_table_raises():
    a = make_table(H, ["1", "Ana", "NY"])
    b = make_table(H, ["", "Ana", "NY"])
    with pytest.raises(ValueError, match="blank"):
        match_rows(a, b, key_col="id")


@pytest.mark.parametrize("bad", [-0.1, 1.1, 2])
def test_threshold_out_of_range_raises(bad):
    t = make_table(H, ["1", "A", "B"])
    with pytest.raises(ValueError, match="threshold"):
        match_rows(t, t, key_col="id", threshold=bad)


# ---------- similarity-based fallback (no key column) ----------

def test_identical_rows_match_without_key():
    a = make_table(H, ["1", "Ana", "NY"], ["2", "Bo", "LA"])
    b = make_table(H, ["2", "Bo", "LA"], ["1", "Ana", "NY"])
    pairs, deleted, inserted = match_rows(a, b)
    assert [(x.cells["id"], y.cells["id"]) for x, y in pairs] == [("1", "1"), ("2", "2")]
    assert deleted == [] and inserted == []


def test_modified_row_matches_when_above_threshold():
    a = make_table(H, ["1", "Ana", "NY"])
    b = make_table(H, ["1", "Ana", "LA"])  # 2/3 = 0.67 similar
    pairs, deleted, inserted = match_rows(a, b, threshold=0.6)
    assert len(pairs) == 1 and deleted == [] and inserted == []


def test_row_below_threshold_is_not_matched():
    a = make_table(H, ["1", "Ana", "NY"])
    b = make_table(H, ["1", "Ana", "LA"])
    pairs, deleted, inserted = match_rows(a, b, threshold=0.7)
    assert pairs == [] and len(deleted) == 1 and len(inserted) == 1


def test_threshold_boundary_is_inclusive():
    a = make_table(["a", "b"], ["1", "x"])
    b = make_table(["a", "b"], ["1", "y"])  # exactly 0.5
    pairs, _, _ = match_rows(a, b, threshold=0.5)
    assert len(pairs) == 1


def test_each_row_matched_at_most_once():
    a = make_table(["a", "b"], ["1", "x"], ["1", "x"])
    b = make_table(["a", "b"], ["1", "x"])
    pairs, deleted, inserted = match_rows(a, b)
    assert len(pairs) == 1 and len(deleted) == 1 and inserted == []


def test_best_similarity_wins():
    a = make_table(H, ["1", "Ana", "NY"])
    b = make_table(H, ["1", "Ana", "LA"], ["1", "Ana", "NY"])
    pairs, _, inserted = match_rows(a, b, threshold=0.5)
    assert pairs[0][1].cells["city"] == "NY"
    assert inserted[0].cells["city"] == "LA"


def test_no_shared_headers_means_nothing_matches():
    a = make_table(["x"], ["1"])
    b = make_table(["y"], ["1"])
    pairs, deleted, inserted = match_rows(a, b)
    assert pairs == [] and len(deleted) == 1 and len(inserted) == 1


def test_only_shared_headers_are_compared():
    a = make_table(["id", "old_col"], ["1", "p"])
    b = make_table(["id", "new_col"], ["1", "q"])
    pairs, _, _ = match_rows(a, b, threshold=1.0)
    assert len(pairs) == 1


def test_fallback_does_not_mutate_inputs():
    a = make_table(H, ["1", "Ana", "NY"])
    b = make_table(H)
    _, deleted, _ = match_rows(make_table(["x"], ["1"]), make_table(["y"], ["1"]))
    deleted.clear()
    match_rows(a, b)
    assert len(a.rows) == 1


# ---------- compute_row_similarity ----------

def test_similarity_all_equal_is_one():
    a = make_table(H, ["1", "Ana", "NY"]).rows[0]
    assert compute_row_similarity(a, a, H) == 1.0


def test_similarity_none_equal_is_zero():
    a = make_table(H, ["1", "Ana", "NY"]).rows[0]
    b = make_table(H, ["2", "Bo", "LA"]).rows[0]
    assert compute_row_similarity(a, b, H) == 0.0


def test_similarity_is_fraction_of_matching_cells():
    a = make_table(H, ["1", "Ana", "NY"]).rows[0]
    b = make_table(H, ["1", "Ana", "LA"]).rows[0]
    assert compute_row_similarity(a, b, H) == pytest.approx(2 / 3)


def test_similarity_empty_headers_is_zero():
    a = make_table(H, ["1", "Ana", "NY"]).rows[0]
    assert compute_row_similarity(a, a, []) == 0.0


def test_similarity_treats_missing_cell_as_empty_string():
    a = make_table(["x"], [""]).rows[0]
    b = make_table(["y"], ["z"]).rows[0]
    assert compute_row_similarity(a, b, ["x"]) == 1.0


def test_similarity_is_symmetric():
    a = make_table(H, ["1", "Ana", "NY"]).rows[0]
    b = make_table(H, ["1", "Bo", "NY"]).rows[0]
    assert compute_row_similarity(a, b, H) == compute_row_similarity(b, a, H)
