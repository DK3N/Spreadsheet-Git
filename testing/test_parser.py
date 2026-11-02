"""Tests for src.parser (Card 1): read_csv / write_csv."""
import pytest

from src.parser import read_csv, write_csv
from src.models import Row, Table


# ---------- valid input ----------

def test_reads_headers_and_rows(write_file):
    table = read_csv(write_file("a.csv", "id,name\n1,Ana\n2,Bo\n"))
    assert table.headers == ["id", "name"]
    assert [r.cells for r in table.rows] == [
        {"id": "1", "name": "Ana"},
        {"id": "2", "name": "Bo"},
    ]


def test_row_indexes_start_at_zero_and_raw_values_kept(write_file):
    table = read_csv(write_file("a.csv", "id,name\n1,Ana\n2,Bo\n"))
    assert [r.row_index for r in table.rows] == [0, 1]
    assert table.rows[1].raw_values == ["2", "Bo"]


def test_accepts_path_string_and_pathlib(write_file):
    path = write_file("a.csv", "id\n1\n")
    assert read_csv(path).rows == read_csv(str(path)).rows


def test_header_only_file_has_no_rows(write_file):
    table = read_csv(write_file("a.csv", "id,name\n"))
    assert table.headers == ["id", "name"]
    assert table.rows == []


def test_quoted_value_containing_comma(write_file):
    table = read_csv(write_file("a.csv", 'id,name\n1,"Smith, Jane"\n'))
    assert table.rows[0].cells["name"] == "Smith, Jane"


def test_quoted_value_with_escaped_quote(write_file):
    table = read_csv(write_file("a.csv", 'id,note\n1,"She said ""hi"""\n'))
    assert table.rows[0].cells["note"] == 'She said "hi"'


def test_quoted_value_with_embedded_newline(write_file):
    table = read_csv(write_file("a.csv", 'id,note\n1,"line1\nline2"\n2,x\n'))
    assert table.rows[0].cells["note"] == "line1\nline2"
    assert len(table.rows) == 2


def test_empty_cells_are_empty_strings(write_file):
    table = read_csv(write_file("a.csv", "a,b,c\n1,,3\n,,\n"))
    assert table.rows[0].cells == {"a": "1", "b": "", "c": "3"}
    assert table.rows[1].cells == {"a": "", "b": "", "c": ""}


def test_all_empty_row_is_kept_but_blank_line_is_skipped(write_file):
    table = read_csv(write_file("a.csv", "a,b\n1,2\n\n,\n3,4\n"))
    assert [r.raw_values for r in table.rows] == [["1", "2"], ["", ""], ["3", "4"]]
    assert [r.row_index for r in table.rows] == [0, 1, 2]


def test_utf8_bom_is_stripped_from_first_header(write_file):
    table = read_csv(write_file("a.csv", b"\xef\xbb\xbfid,name\n1,Ana\n"))
    assert table.headers == ["id", "name"]


def test_unicode_values(write_file):
    table = read_csv(write_file("a.csv", "id,name\n1,José 日本\n"))
    assert table.rows[0].cells["name"] == "José 日本"


def test_windows_line_endings(write_file):
    table = read_csv(write_file("a.csv", "id,name\r\n1,Ana\r\n2,Bo\r\n"))
    assert [r.cells["name"] for r in table.rows] == ["Ana", "Bo"]


def test_no_trailing_newline(write_file):
    table = read_csv(write_file("a.csv", "id,name\n1,Ana"))
    assert len(table.rows) == 1


def test_whitespace_in_values_is_preserved(write_file):
    table = read_csv(write_file("a.csv", "id,name\n1, Ana \n"))
    assert table.rows[0].cells["name"] == " Ana "


# ---------- errors ----------

def test_missing_file_raises_file_not_found(tmp_path):
    with pytest.raises(FileNotFoundError):
        read_csv(tmp_path / "nope.csv")


def test_directory_path_raises_os_error(tmp_path):
    with pytest.raises(OSError):
        read_csv(tmp_path)


def test_empty_file_raises_value_error(write_file):
    with pytest.raises(ValueError, match="empty"):
        read_csv(write_file("a.csv", ""))


def test_blank_header_raises(write_file):
    with pytest.raises(ValueError, match="header"):
        read_csv(write_file("a.csv", "id,,name\n1,2,3\n"))


def test_whitespace_only_header_raises(write_file):
    with pytest.raises(ValueError, match="header"):
        read_csv(write_file("a.csv", "id, \n1,2\n"))


def test_duplicate_headers_raise(write_file):
    with pytest.raises(ValueError, match="unique"):
        read_csv(write_file("a.csv", "id,id\n1,2\n"))


def test_row_with_too_few_values_raises_with_line_info(write_file):
    with pytest.raises(ValueError, match=r"line 3.*1 values; expected 2"):
        read_csv(write_file("a.csv", "id,name\n1,Ana\n2\n"))


def test_row_with_too_many_values_raises(write_file):
    with pytest.raises(ValueError, match="expected 2"):
        read_csv(write_file("a.csv", "id,name\n1,Ana,extra\n"))


def test_unterminated_quote_raises_value_error(write_file):
    with pytest.raises(ValueError, match="Invalid CSV"):
        read_csv(write_file("a.csv", 'id,name\n1,"unclosed\n'))


# ---------- write_csv ----------

def test_write_then_read_round_trip(tmp_path, write_file):
    original = read_csv(write_file(
        "in.csv", 'id,name,note\n1,"Smith, Jane","a ""b"""\n2,,"x\ny"\n'
    ))
    out = tmp_path / "out.csv"
    write_csv(original, out)
    again = read_csv(out)
    assert again.headers == original.headers
    assert [r.cells for r in again.rows] == [r.cells for r in original.rows]


def test_write_quotes_only_when_needed(tmp_path):
    table = Table(
        headers=["id", "name"],
        rows=[Row(0, {"id": "1", "name": "Smith, Jane"}, ["1", "Smith, Jane"])],
    )
    out = tmp_path / "out.csv"
    write_csv(table, out)
    assert out.read_text(encoding="utf-8") == 'id,name\n1,"Smith, Jane"\n'


def test_write_uses_table_delimiter_and_terminator(tmp_path):
    table = Table(
        headers=["a", "b"],
        rows=[Row(0, {"a": "1", "b": "2"}, ["1", "2"])],
        delimiter=";",
        line_terminator="\r\n",
    )
    out = tmp_path / "out.csv"
    write_csv(table, out)
    assert out.read_bytes() == b"a;b\r\n1;2\r\n"


def test_write_fills_missing_cells_with_empty_string(tmp_path):
    table = Table(headers=["a", "b"], rows=[Row(0, {"a": "1"}, ["1"])])
    out = tmp_path / "out.csv"
    write_csv(table, out)
    assert out.read_text(encoding="utf-8") == "a,b\n1,\n"


def test_write_follows_header_order_not_dict_order(tmp_path):
    table = Table(headers=["a", "b"], rows=[Row(0, {"b": "2", "a": "1"}, [])])
    out = tmp_path / "out.csv"
    write_csv(table, out)
    assert out.read_text(encoding="utf-8") == "a,b\n1,2\n"


def test_write_to_missing_directory_raises(tmp_path):
    with pytest.raises(OSError):
        write_csv(Table(headers=["a"], rows=[]), tmp_path / "no_dir" / "out.csv")
