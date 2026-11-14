"""Command line entry point: simple-manifest manifest.json|csv [--output file]."""

import argparse
import sys
from pathlib import Path

from simple_manifest_validator import __version__
from simple_manifest_validator.formatting import format_report
from simple_manifest_validator.manifest import ManifestError, build_report, load_manifest


def build_parser() -> argparse.ArgumentParser:
    """Create the argument parser."""
    parser = argparse.ArgumentParser(
        prog="simple-manifest",
        description="Validate a FilaFácil cargo manifest (JSON or CSV).",
    )
    parser.add_argument("manifest_file", type=Path, help="Manifest file (.json or .csv)")
    parser.add_argument("--output", type=Path, help="Also write the report to this file")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run the CLI. Return 0 when a report is produced and 1 when the file cannot be used."""
    args = build_parser().parse_args(argv)
    try:
        text = format_report(build_report(load_manifest(args.manifest_file)))
        if args.output is not None:
            args.output.write_text(text, encoding="utf-8")
    except ManifestError as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1
    except OSError as error:
        print(f"Error: could not write {args.output}: {error.strerror}", file=sys.stderr)
        return 1
    print(text, end="")
    return 0
