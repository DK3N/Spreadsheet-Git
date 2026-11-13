"""End-to-end tests (Card 10): run the real CLI on sample CSV files and check the output."""
import subprocess
import sys
from pathlib import Path

from src.cli import EXIT_ERROR, EXIT_OK, main

CASES = Path(__file__).parent / "test_cases"
REPO_ROOT = Path(__file__).parent.parent


def run_diff(case, capsys, *extra):
    """Run `diff` on a case folder and return (exit_code, stdout, stderr)."""
    folder = CASES / case
    code = main(["diff", str(folder / "base.csv"), str(folder / "modified.csv"), "--key", "id", *extra])
    out, err = capsys.readouterr()
    return code, out, err


# ---------- diff on sample files ----------

def test_example_case_reports_every_change_type(capsys):
    code, out, _ = run_diff("test_case_example", capsys)
    assert code == EXIT_OK
    assert "MODIFIED  key=103" in out
    assert "salary: '91000' -> '95000'" in out
    assert "INSERTED  key=109" in out
    assert "DELETED  key=106" in out
    assert "MOVED  key=102" in out
    assert "department: 'Sales' -> 'Marketing'" in out
    assert "Summary: 1 added, 1 removed, 2 modified, 1 moved" in out


def test_example_case_matches_expected_diff_file(capsys):
    """Every key in expected_diff.json shows up in the CLI output with the same change type."""
    import json
    expected = json.loads((CASES / "test_case_example" / "expected_diff.json").read_text())
    _, out, _ = run_diff("test_case_example", capsys)
    for change in expected["changes"]:
        label = change["change_type"].replace("_", " ")
        assert f"{label}  key={change['key_value']}" in out


def test_reordered_rows_are_not_reported_as_modified(capsys):
    code, out, _ = run_diff("reordered_only", capsys)
    assert code == EXIT_OK
    assert "MODIFIED" not in out
    assert "INSERTED" not in out
    assert "DELETED" not in out


def test_identical_files_report_no_differences(capsys):
    folder = CASES / "test_case_example"
    code = main(["diff", str(folder / "base.csv"), str(folder / "base.csv"), "--key", "id"])
    out, _ = capsys.readouterr()
    assert code == EXIT_OK
    assert out.strip() == "No differences found."


def test_quoted_values_and_embedded_newlines(capsys):
    code, out, _ = run_diff("quoted_values", capsys)
    assert code == EXIT_OK
    assert "MODIFIED  key=1" in out
    assert "note: 'said \"hi\"' -> 'said \"bye\"'" in out
    assert "INSERTED  key=3" in out
    assert "Summary: 1 added, 0 removed, 1 modified" in out


def test_no_color_flag_removes_ansi_codes(capsys):
    _, out, _ = run_diff("test_case_example", capsys, "--no-color")
    assert "\033[" not in out


# ---------- the real command line ----------

def run_cli(*args):
    return subprocess.run(
        [sys.executable, "-m", "src.cli", *args],
        cwd=REPO_ROOT, capture_output=True, text=True,
    )


def test_cli_runs_as_a_command():
    folder = CASES / "test_case_example"
    result = run_cli("diff", str(folder / "base.csv"), str(folder / "modified.csv"), "--key", "id")
    assert result.returncode == EXIT_OK
    assert "Summary:" in result.stdout
    assert result.stderr == ""


def test_missing_arguments_show_usage():
    result = run_cli("diff")
    assert result.returncode == EXIT_ERROR
    assert "usage:" in result.stderr


def test_missing_file_gives_clear_error_and_exit_code_2():
    folder = CASES / "test_case_example"
    result = run_cli("diff", str(folder / "base.csv"), "does_not_exist.csv", "--key", "id")
    assert result.returncode == EXIT_ERROR
    assert "file not found" in result.stderr
    assert "Traceback" not in result.stderr


# ---------- bad input gives a clear error, not a traceback ----------

def test_duplicate_ids_give_clear_error(tmp_path):
    bad = tmp_path / "dup.csv"
    bad.write_text("id,name\n1,a\n1,b\n")
    good = CASES / "test_case_example" / "base.csv"
    result = run_cli("diff", str(bad), str(good), "--key", "id")
    assert result.returncode == EXIT_ERROR
    assert "duplicate" in result.stderr
    assert "Traceback" not in result.stderr


def test_malformed_csv_gives_clear_error(tmp_path):
    bad = tmp_path / "bad.csv"
    bad.write_text("id,name\n1,a\n2\n")
    good = CASES / "test_case_example" / "base.csv"
    result = run_cli("diff", str(bad), str(good), "--key", "id")
    assert result.returncode == EXIT_ERROR
    assert "Traceback" not in result.stderr


def test_unknown_key_column_gives_clear_error():
    folder = CASES / "test_case_example"
    result = run_cli("diff", str(folder / "base.csv"), str(folder / "modified.csv"), "--key", "nope")
    assert result.returncode == EXIT_ERROR
    assert "error:" in result.stderr
    assert "Traceback" not in result.stderr


def test_key_is_required():
    folder = CASES / "test_case_example"
    result = run_cli("diff", str(folder / "base.csv"), str(folder / "modified.csv"))
    assert result.returncode == EXIT_ERROR
    assert "--key" in result.stderr
