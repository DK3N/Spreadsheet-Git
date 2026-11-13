"""
PURPOSE: To serve as the CLI entry point, parsing terminal flags/subcommands and dispatching execution to diff, merge, or test workflows with appropriate exit codes.
FUNCTIONS:
- build_parser: Sets up argparse command-line arguments, subcommands (diff, merge), and options like --key and --output.
- run_diff: Orchestrates the read, diff, and terminal rendering pipeline for a 2-way comparison.
- run_merge: Orchestrates the 3-way file read, merge resolution, output serialization, and conflict status reporting.
- main: Top-level entry function executed when the tool is invoked from the command line.
"""

import argparse
import sys
from typing import Optional

from . import differ, merger, printer
from . import parser as csv_parser

EXIT_OK = 0
EXIT_CONFLICTS = 1
EXIT_ERROR = 2


def build_parser() -> argparse.ArgumentParser:
    """Constructs and returns the top-level argument parser with subcommands."""
    top = argparse.ArgumentParser(prog="csvdiff3", description="Diff and merge CSV files.")
    sub = top.add_subparsers(dest="command", required=True)

    diff_cmd = sub.add_parser("diff", help="compare two CSV files")
    diff_cmd.add_argument("file_a", help="the original CSV")
    diff_cmd.add_argument("file_b", help="the changed CSV")
    diff_cmd.add_argument("--key", required=True, help="column that uniquely identifies a row, e.g. id")
    diff_cmd.add_argument("--no-color", action="store_true", help="turn off colored output")

    merge_cmd = sub.add_parser("merge", help="3-way merge of two edited CSVs")
    merge_cmd.add_argument("base", help="the common ancestor CSV")
    merge_cmd.add_argument("ours", help="our edited CSV")
    merge_cmd.add_argument("theirs", help="their edited CSV")
    merge_cmd.add_argument("--key", required=True, help="column that uniquely identifies a row")
    merge_cmd.add_argument("--output", default="merged.csv", help="where to write the result")
    return top


def run_diff(args: argparse.Namespace) -> int:
    """Handles execution of the 2-way diff pipeline and prints output to stdout."""
    try:
        table_a = csv_parser.read_csv(args.file_a)
        table_b = csv_parser.read_csv(args.file_b)
        result = differ.compute_diff(table_a, table_b, key_col=args.key)
    except FileNotFoundError as err:
        print(f"error: file not found: {err.filename}", file=sys.stderr)
        return EXIT_ERROR
    except OSError as err:
        print(f"error: cannot read {err.filename}: {err.strerror}", file=sys.stderr)
        return EXIT_ERROR
    except ValueError as err:
        print(f"error: {err}", file=sys.stderr)
        return EXIT_ERROR

    use_color = sys.stdout.isatty() and not args.no_color
    print(printer.render_diff_terminal(result, use_color=use_color))
    return EXIT_OK


def run_merge(args: argparse.Namespace) -> int:
    """Handles execution of the 3-way merge pipeline and writes the output file."""
    try:
        base = csv_parser.read_csv(args.base)
        ours = csv_parser.read_csv(args.ours)
        theirs = csv_parser.read_csv(args.theirs)
        result = merger.three_way_merge(base, ours, theirs, args.key)
        csv_parser.write_csv(result.merged_table, args.output)
    except FileNotFoundError as err:
        print(f"error: file not found: {err.filename}", file=sys.stderr)
        return EXIT_ERROR
    except OSError as err:
        print(f"error: cannot access {err.filename}: {err.strerror}", file=sys.stderr)
        return EXIT_ERROR
    except ValueError as err:
        print(f"error: {err}", file=sys.stderr)
        return EXIT_ERROR

    if result.has_conflicts:
        print(f"Merged with {len(result.conflicts)} conflict(s). Wrote {args.output}")
        for c in result.conflicts:
            print(f"  key={c.key_value} column={c.column_name}")
        return EXIT_CONFLICTS

    print(f"Merged cleanly. Wrote {args.output}")
    return EXIT_OK


def main(argv: Optional[list[str]] = None) -> int:
    """Parses sys.argv and routes execution to the chosen subcommand."""
    args = build_parser().parse_args(argv)
    if args.command == "diff":
        return run_diff(args)
    if args.command == "merge":
        return run_merge(args)
    return EXIT_ERROR


if __name__ == "__main__":
    import sys
    sys.exit(main())