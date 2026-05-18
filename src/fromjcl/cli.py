# SPDX-License-Identifier: Apache-2.0
"""Command-line interface for fromjcl."""

import argparse
import sys

from fromjcl.models import Job
from fromjcl.parser import parse, parse_bytes
from fromjcl.serialize import csv as csv_out
from fromjcl.serialize import jcl as jcl_out
from fromjcl.serialize import json as json_out
from fromjcl.serialize import raw as raw_out
from fromjcl.serialize import yaml as yaml_out

ZOAU_FORMATS = {"mvscmd", "zoau"}


def _require_extra(extra: str, marker_module: str) -> None:
    """Exit with help if pip install fromjcl[<extra>] hasn't been run."""
    try:
        __import__(marker_module)
    except ImportError:
        raise SystemExit(
            f"fromjcl: this output format requires the '{extra}' extra.\n"
            f"  Install with: pip install 'fromjcl[{extra}]'"
        ) from None


def _write_output(output: str, dest: str | None) -> int:
    """Write output to a file or stdout, ensuring a trailing newline on file output."""
    if dest:
        with open(dest, "w") as f:
            f.write(output)
            if not output.endswith("\n"):
                f.write("\n")
    else:
        print(output)
    return 0


def main() -> int:
    """fromjcl CLI entry point."""
    argparser = argparse.ArgumentParser(
        prog="fromjcl",
        description="Parse IBM z/OS JCL and serialize to JSON, YAML, CSV, or roundtrip JCL.",
    )
    argparser.add_argument(
        "input",
        nargs="?",
        help="Input file. Use '-' or omit to read stdin.",
    )
    argparser.add_argument(
        "--rejcl",
        action="store_true",
        help="Reverse mode: read a yaml/json/csv Job dump and emit JCL.",
    )
    argparser.add_argument(
        "--from",
        dest="from_fmt",
        choices=["yaml", "json", "csv"],
        help="Input format for --rejcl (auto-detected if omitted).",
    )
    argparser.add_argument(
        "--to",
        choices=["json", "yaml", "csv", "jcl", "raw", "zoau", "mvscmd"],
        default="json",
        help="Output format (default: json). zoau/mvscmd require the [zoau] extra.",
    )
    argparser.add_argument(
        "-o",
        "--output",
        help="Output file (default: stdout)",
    )
    argparser.add_argument(
        "--strict",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Exit non-zero on validation warnings (default).",
    )

    args = argparser.parse_args()
    fmt = args.to

    if args.rejcl:
        from fromjcl import rejcl

        if not args.input or args.input == "-":
            if sys.stdin.isatty():
                argparser.print_help(sys.stderr)
                return 2
            text = sys.stdin.read()
        else:
            with open(args.input) as f:
                text = f.read()
        try:
            output = rejcl.convert(text, args.from_fmt)
        except (ValueError, KeyError) as e:
            print(f"Error: {e}", file=sys.stderr)
            return 1
        return _write_output(output, args.output)

    try:
        if not args.input or args.input == "-":
            if sys.stdin.isatty():
                argparser.print_help(sys.stderr)
                return 2
            parsed = parse_bytes(sys.stdin.buffer.read())
        else:
            parsed = parse(args.input)
    except RuntimeError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    warnings: list[str] = []
    if fmt == "raw":
        output = raw_out.convert(parsed)
    elif fmt == "json":
        output = json_out.convert(Job.from_parsed(parsed))
    elif fmt == "yaml":
        output = yaml_out.convert(Job.from_parsed(parsed))
    elif fmt == "csv":
        output = csv_out.convert(Job.from_parsed(parsed))
    elif fmt == "jcl":
        output = jcl_out.convert(parsed)
    elif fmt in ZOAU_FORMATS:
        _require_extra("zoau", "bashlex")
        from fromjcl import _validate
        from fromjcl.converters.shell import mvscmd, zoau

        job = Job.from_parsed(parsed)
        output = (mvscmd if fmt == "mvscmd" else zoau).convert(job)
        warnings = _validate.validate_shell(output)
        output = _validate.prepend_warnings(output, warnings, comment_prefix="#")
    else:
        output = ""

    _write_output(output, args.output)

    if warnings:
        print(f"fromjcl: validation failed ({len(warnings)} issue(s)):", file=sys.stderr)
        for w in warnings:
            print(f"  - {w}", file=sys.stderr)
        if args.strict:
            return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
