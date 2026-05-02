"""Command-line interface for fromjcl."""

import argparse
import sys

from fromjcl.models import Job
from fromjcl.parser import parse
from fromjcl.serialize import csv as csv_out
from fromjcl.serialize import jcl as jcl_out
from fromjcl.serialize import json as json_out
from fromjcl.serialize import raw as raw_out
from fromjcl.serialize import yaml as yaml_out


def main() -> int:
    """fromjcl CLI entry point."""
    argparser = argparse.ArgumentParser(
        prog="fromjcl",
        description="Parse IBM z/OS JCL and serialize to JSON, YAML, CSV, or roundtrip JCL.",
    )
    argparser.add_argument("input", help="Input JCL file")
    argparser.add_argument(
        "--to",
        choices=["json", "yaml", "csv", "raw", "jcl"],
        default="json",
        help="Output format (default: json)",
    )
    argparser.add_argument(
        "-o",
        "--output",
        help="Output file (default: stdout)",
    )

    args = argparser.parse_args()
    fmt = args.to

    try:
        parsed = parse(args.input)
    except RuntimeError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

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
    else:
        output = ""

    if args.output:
        with open(args.output, "w") as f:
            f.write(output)
            if not output.endswith("\n"):
                f.write("\n")
    else:
        print(output)

    return 0


if __name__ == "__main__":
    sys.exit(main())
