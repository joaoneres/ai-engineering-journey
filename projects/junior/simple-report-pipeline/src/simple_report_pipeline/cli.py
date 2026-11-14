"""Command line entry point: simple-report pickups.json [--format text|json]."""

import argparse
import json
import sys
from pathlib import Path

from simple_report_pipeline import __version__
from simple_report_pipeline.formatting import format_summary
from simple_report_pipeline.report import ReportError, build_summary, load_pickups


def build_parser() -> argparse.ArgumentParser:
    """Create the argument parser."""
    parser = argparse.ArgumentParser(
        prog="simple-report", description="Operational report for FilaFácil pickups."
    )
    parser.add_argument("pickups_file", type=Path, help="JSON file with the pickups")
    parser.add_argument("--format", choices=("text", "json"), default="text")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run the CLI; return 0 on success and 1 if the file cannot be used."""
    args = build_parser().parse_args(argv)
    try:
        summary = build_summary(load_pickups(args.pickups_file))
    except ReportError as error:
        print(f"Erro: {error}", file=sys.stderr)
        return 1
    if args.format == "json":
        print(json.dumps(summary, indent=2, ensure_ascii=False))
    else:
        print(format_summary(summary))
    return 0
