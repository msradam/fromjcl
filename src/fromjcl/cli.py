"""Command-line interface for fromjcl."""

import argparse
import json
import sys

import yaml

from fromjcl.parser import parse
from fromjcl.models import Job
from fromjcl.converters import mvscmd, ansible


def main():
    argparser = argparse.ArgumentParser(
        prog="fromjcl",
        description="Convert JCL to modern formats",
    )
    argparser.add_argument("input", help="Input JCL file")
    argparser.add_argument(
        "--to",
        choices=["json", "yaml", "mvscmd", "ansible", "raw"],
        default="json",
        help="Output format (default: json)",
    )
    argparser.add_argument(
        "-o",
        "--output",
        help="Output file (default: stdout)",
    )

    args = argparser.parse_args()

    try:
        parsed = parse(args.input)
    except RuntimeError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    if args.to == "raw":
        output = json.dumps(parsed, indent=2)
    elif args.to == "json":
        job = Job.from_parsed(parsed)
        output = json.dumps(job.to_dict(), indent=2, default=str)
    elif args.to == "yaml":
        job = Job.from_parsed(parsed)
        output = yaml.dump(job.to_dict(), default_flow_style=False, sort_keys=False)
    elif args.to == "mvscmd":
        job = Job.from_parsed(parsed)
        output = mvscmd.convert(job)
    elif args.to == "ansible":
        job = Job.from_parsed(parsed)
        output = ansible.convert(job)

    if args.output:
        with open(args.output, "w") as f:
            f.write(output)
            f.write("\n")
    else:
        print(output)

    return 0


if __name__ == "__main__":
    sys.exit(main())
