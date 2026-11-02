# Simple-Spreadsheet-Git

A command-line tool that compares two CSV files and reports which rows were added, removed, or modified. Think `git diff`, but for spreadsheets. Built for Capstone I at Florida International University.

Rows are matched by an ID column you choose, so reordering rows is not mistaken for a change.

> **Status:** in development (Sprint 1). The data models, tests, and CI are in place; the parser, matcher, differ, and CLI are being implemented. Usage below describes the intended interface and may change as the CLI lands.

## What it does

Given an old CSV, a new CSV, and an ID column, the tool reports:

- **Added** rows: IDs that appear only in the new file
- **Removed** rows: IDs that appear only in the old file
- **Modified** rows: same ID in both files, with the old and new value of each changed column
- Summary counts for each of the above

Planned for Sprint 2: schema changes (added, removed, reordered columns), comparing only selected columns, JSON report export, and grouped, readable terminal output.

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

## Usage (planned)

```bash
python -m src.cli <old.csv> <new.csv> --key <id_column>
```

Example, comparing two versions of a roster keyed on `id`:

```bash
python -m src.cli roster_old.csv roster_new.csv --key id
```

Expected output shape:

```
Added: 1   Removed: 1   Modified: 2

Modified
  id=3  name: "Ana" -> "Anna"
  id=7  city: "NY" -> "LA"
```

Errors (missing file, malformed CSV, duplicate or blank IDs, unknown column) are reported with a clear message instead of a traceback.

## Project layout

| Path | Purpose |
|---|---|
| `src/models.py` | Shared data classes (`Table`, `Row`, `RowChange`, `DiffResult`, ...) |
| `src/parser.py` | Read and write CSV files (quotes, embedded commas/newlines, UTF-8 BOM) |
| `src/matcher.py` | Pair rows between two files by ID column |
| `src/differ.py` | Classify added, removed, and modified rows and their cell changes |
| `src/printer.py` | Render results for the terminal |
| `src/cli.py` | Command-line entry point |
| `testing/` | Automated tests and sample CSV fixtures |

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

GitHub Actions (`.github/workflows/tests.yml`) runs `python -m pytest` on every push and pull request. Run the tests locally before opening a PR. While features are still being merged, some tests will fail until the matching module is implemented.

## Known limitations

- Rows must have a unique, non-blank value in the ID column.
- Both files must be valid CSV with a header row and the same number of values on every row.
- All values are compared as text (`1` and `01` are different).

## Team

Zackary, David, Joseph, Sarah, Emely
