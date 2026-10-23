"""
PURPOSE: To serve as the CLI entry point, parsing terminal flags/subcommands and dispatching execution to diff, merge, or test workflows with appropriate exit codes.
FUNCTIONS:
- build_parser: Sets up argparse command-line arguments, subcommands (diff, merge), and options like --key and --output.
- run_diff: Orchestrates the read, diff, and terminal rendering pipeline for a 2-way comparison.
- run_merge: Orchestrates the 3-way file read, merge resolution, output serialization, and conflict status reporting.
- main: Top-level entry function executed when the tool is invoked from the command line.
"""

import argparse
from typing import Optional


def build_parser() -> argparse.ArgumentParser:
    """Constructs and returns the top-level argument parser with subcommands."""
    # TODO: Configure argparse with 'diff' and 'merge' subcommands
    return argparse.ArgumentParser(prog="csvdiff3")


def run_diff(args: argparse.Namespace) -> int:
    """Handles execution of the 2-way diff pipeline and prints output to stdout."""
    # TODO: Call parser.read_csv -> differ.compute_diff -> formatters.render_diff_terminal
    return 0


def run_merge(args: argparse.Namespace) -> int:
    """Handles execution of the 3-way merge pipeline and writes the output file."""
    # TODO: Call parser.read_csv -> merger.three_way_merge -> parser.write_csv
    return 0


def main(argv: Optional[list[str]] = None) -> int:
    """Parses sys.argv and routes execution to the chosen subcommand."""
    # TODO: Dispatch args to run_diff or run_merge and return exit code
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())