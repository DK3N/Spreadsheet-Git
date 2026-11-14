# Simple-Spreadsheet-Git

A command-line tool that compares two CSV files and reports which rows were added, removed, or modified. Think `git diff`, but for spreadsheets. Built for Capstone I at Florida International University.

Rows are matched by an ID column you choose, so reordering rows is not mistaken for a change.

> **Status:** Sprint 1 is merged: CSV parsing, row matching, row diffing, the CLI, and automated tests with CI. Sprint 2 work is in progress: schema change detection is merged; column filtering, JSON export, and clearer output are still to come.

## What it does

Given an old CSV, a new CSV, and an ID column, the tool reports:

- **Added** rows: IDs that appear only in the new file
- **Removed** rows: IDs that appear only in the old file
- **Modified** rows: same ID in both files, with the old and new value of each changed column
- Summary counts for each of the above

Schema changes are also reported: columns added to or removed from the new file, and whether the columns were reordered (reordering alone is not reported as row changes).

Planned for Sprint 2: comparing only selected columns, JSON report export, and grouped, readable terminal output.

Out of scope: a graphical interface, full version history, merge-conflict resolution, and live collaboration.

## Installation

Requires Python 3.10+.

```bash
git clone https://github.com/DK3N/Spreadsheet-Git.git
cd Spreadsheet-Git
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
python -m pip install -r requirements-dev.txt
```

The tool itself uses only the Python standard library; `requirements-dev.txt` installs the test tools.

## Usage

```bash
python -m src.cli diff <old.csv> <new.csv> --key <id_column>
```

Example, using the sample files in this repo:

```bash
python -m src.cli diff testing/test_cases/test_case_example/base.csv testing/test_cases/test_case_example/modified.csv --key id
```

Output:

```
~ MODIFIED  key=103  (row 4 -> row 3)
    salary: '91000' -> '95000'
+ INSERTED  key=109  (now row 4)
> MOVED  key=102  (row 3 -> row 8)
~> MOVED AND MODIFIED  key=104  (row 5 -> row 9)
    department: 'Sales' -> 'Marketing'
- DELETED  key=106  (was row 7)

Summary: 1 added, 1 removed, 2 modified, 1 moved
```

Options:

| Option | What it does |
|---|---|
| `--key <column>` | Required. Column that uniquely identifies a row. Rows are matched by this value. |
| `--no-color` | Turn off colored output (color is also off when output is piped). |
| `-h`, `--help` | Show usage help. |

Exit codes: `0` success, `2` error (for example a missing file, a malformed CSV, duplicate or blank IDs, an unknown key column, or missing arguments). Errors print a one-line `error: ...` message.

## Project layout

| Path | Purpose |
|---|---|
| `src/models.py` | Shared data classes (`Table`, `Row`, `RowChange`, `DiffResult`, ...) |
| `src/parser.py` | Read and write CSV files (quotes, embedded commas/newlines, UTF-8 BOM) |
| `src/matcher.py` | Pair rows between two files by ID column |
| `src/differ.py` | Classify added, removed, and modified rows and their cell changes |
| `src/printer.py` | Render results for the terminal |
| `src/cli.py` | Command-line entry point |
| `testing/` | Unit tests, end-to-end tests (`test_end_to_end.py`), and sample CSV fixtures in `test_cases/` |

## Running tests

From the repository root:

```bash
python -m pytest
```

Tests live in `testing/` and are named `test_*.py`. They import project code as `src.<module>` (for example `from src.parser import read_csv`); `pytest.ini` puts the repo root on the path, so no install step is needed.

Useful variations:

```bash
python -m pytest testing/test_matcher.py   # one file
python -m pytest -k duplicate              # tests matching a name
python -m pytest -x                        # stop at first failure
```

Sample CSV fixtures go in `testing/test_cases/<case_name>/` (`base.csv`, `modified.csv`, `expected_diff.json`). Shared helpers (`make_table`, `write_file`) are in `testing/conftest.py`.

## Continuous integration

GitHub Actions (`.github/workflows/tests.yml`) runs `python -m pytest` on every push and pull request. Run the tests locally before opening a PR.

## Known limitations

- Rows must have a unique, non-blank value in the ID column.
- Column filtering and JSON export are not available yet (Sprint 2).
- Both files must be valid CSV with a header row and the same number of values on every row.
- All values are compared as text (`1` and `01` are different).

## Team

Zackary, David, Joseph, Sarah, Emely
