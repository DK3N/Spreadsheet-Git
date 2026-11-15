"""Tests for src/exporter.py and `diff --json` (card #1570: export comparison reports as JSON)."""
import json
from pathlib import Path

from src.cli import EXIT_ERROR, EXIT_OK, main
from src.differ import compute_diff
from src.exporter import build_report, write_json_report
from src.parser import read_csv

EXAMPLE = Path(__file__).parent / "test_cases" / "test_case_example"
BASE = str(EXAMPLE / "base.csv")
MODIFIED = str(EXAMPLE / "modified.csv")


def example_diff():
    return compute_diff(read_csv(BASE), read_csv(MODIFIED), key_col="id")


def csv_text(*lines):
    return "\n".join(lines) + "\n"


# ---------- report contents ----------

def test_changes_match_expected_diff_fixture():
    expected = json.loads((EXAMPLE / "expected_diff.json").read_text(encoding="utf-8"))
    report = build_report(example_diff(), key_col="id")
    assert report["key_col"] == expected["key_col"]
    assert report["changes"] == expected["changes"]


def test_modified_rows_include_old_and_new_values():
    report = build_report(example_diff(), key_col="id")
    row = next(c for c in report["changes"] if c["key_value"] == "103")
    assert row["change_type"] == "MODIFIED"
    assert row["cell_changes"] == [{"column_value": "salary", "old_value": "91000", "new_value": "95000"}]


def test_summary_counts():
    report = build_report(example_diff(), key_col="id")
    assert report["summary"] == {"added": 1, "removed": 1, "modified": 2, "moved": 1}


def test_column_changes_are_included(write_file):
    a = write_file("a.csv", csv_text("id,name,qty", "1,apple,5"))
    b = write_file("b.csv", csv_text("id,qty,note", "1,5,fresh"))
    report = build_report(compute_diff(read_csv(a), read_csv(b), key_col="id"), key_col="id")
    assert report["columns"]["added"] == ["note"]
    assert report["columns"]["removed"] == ["name"]


def test_reordered_columns_are_flagged():
    case = EXAMPLE.parent / "columns_reordered"
    diff = compute_diff(read_csv(case / "base.csv"), read_csv(case / "modified.csv"), key_col="id")
    report = build_report(diff, key_col="id")
    assert report["columns"]["reordered"] is True
    assert report["changes"] == []


def test_no_differences_gives_empty_report():
    table = read_csv(BASE)
    report = build_report(compute_diff(table, read_csv(BASE), key_col="id"), key_col="id")
    assert report["changes"] == []
    assert report["summary"] == {"added": 0, "removed": 0, "modified": 0, "moved": 0}
    assert report["columns"] == {"added": [], "removed": [], "reordered": False}


# ---------- valid JSON on disk ----------

def test_written_file_is_valid_json(tmp_path):
    out = tmp_path / "report.json"
    write_json_report(example_diff(), out, key_col="id", file_a=BASE, file_b=MODIFIED)
    report = json.loads(out.read_text(encoding="utf-8"))
    assert report == build_report(example_diff(), key_col="id", file_a=BASE, file_b=MODIFIED)


def test_special_characters_survive(write_file, tmp_path):
    a = write_file("a.csv", csv_text("id,name", '1,"Ana, ""the boss"""'))
    b = write_file("b.csv", csv_text("id,name", "1,José Núñez"))
    out = tmp_path / "report.json"
    write_json_report(compute_diff(read_csv(a), read_csv(b), key_col="id"), out, key_col="id")
    cell = json.loads(out.read_text(encoding="utf-8"))["changes"][0]["cell_changes"][0]
    assert (cell["old_value"], cell["new_value"]) == ('Ana, "the boss"', "José Núñez")


# ---------- CLI ----------

def test_cli_json_writes_report_and_still_prints_diff(tmp_path, capsys):
    out = tmp_path / "report.json"
    assert main(["diff", BASE, MODIFIED, "--key", "id", "--json", str(out)]) == EXIT_OK
    stdout = capsys.readouterr().out
    assert "Summary: 1 added, 1 removed, 2 modified, 1 moved" in stdout
    assert f"JSON report saved to {out}" in stdout
    report = json.loads(out.read_text(encoding="utf-8"))
    assert (report["file_a"], report["file_b"], report["key_col"]) == (BASE, MODIFIED, "id")
    assert report["summary"]["added"] == 1


def test_cli_without_json_writes_nothing(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    assert main(["diff", BASE, MODIFIED, "--key", "id"]) == EXIT_OK
    assert list(tmp_path.iterdir()) == []


def test_cli_json_to_bad_path_is_an_error(tmp_path, capsys):
    out = tmp_path / "missing_folder" / "report.json"
    assert main(["diff", BASE, MODIFIED, "--key", "id", "--json", str(out)]) == EXIT_ERROR
    assert "error: cannot write" in capsys.readouterr().err
    assert not out.exists()


def test_cli_json_to_a_folder_is_an_error(tmp_path, capsys):
    assert main(["diff", BASE, MODIFIED, "--key", "id", "--json", str(tmp_path)]) == EXIT_ERROR
    assert "error: cannot write" in capsys.readouterr().err


def test_cli_json_will_not_overwrite_an_input(write_file, capsys):
    a = write_file("a.csv", csv_text("id,qty", "1,5"))
    b = write_file("b.csv", csv_text("id,qty", "1,6"))
    before = b.read_text(encoding="utf-8")
    assert main(["diff", str(a), str(b), "--key", "id", "--json", str(b)]) == EXIT_ERROR
    assert "must not be one of the input files" in capsys.readouterr().err
    assert b.read_text(encoding="utf-8") == before
