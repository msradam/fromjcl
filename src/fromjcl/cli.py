# SPDX-License-Identifier: Apache-2.0
"""Command-line interface for fromjcl."""

from __future__ import annotations

import sys
from enum import StrEnum
from pathlib import Path
from typing import Annotated

import typer

from fromjcl.models import Job
from fromjcl.parser import parse, parse_bytes
from fromjcl.serialize import csv as csv_out
from fromjcl.serialize import jcl as jcl_out
from fromjcl.serialize import json as json_out
from fromjcl.serialize import raw as raw_out
from fromjcl.serialize import yaml as yaml_out


class OutputFormat(StrEnum):
    """Forward-path target formats. zoau/mvscmd need the [zoau] extra."""

    json = "json"
    yaml = "yaml"
    csv = "csv"
    jcl = "jcl"
    raw = "raw"
    zoau = "zoau"
    mvscmd = "mvscmd"


class InputFormat(StrEnum):
    """Reverse-path source formats for --rejcl."""

    yaml = "yaml"
    json = "json"
    csv = "csv"


_ZOAU_FORMATS = {OutputFormat.mvscmd, OutputFormat.zoau}


def _require_extra(extra: str, marker_module: str) -> None:
    """Exit with help if pip install fromjcl[<extra>] hasn't been run."""
    try:
        __import__(marker_module)
    except ImportError:
        typer.echo(
            f"fromjcl: this output format requires the '{extra}' extra.\n"
            f"  Install with: pip install 'fromjcl[{extra}]'",
            err=True,
        )
        raise typer.Exit(code=2) from None


def _write_output(output: str, dest: str | None) -> None:
    """Write output to a file or stdout, ensuring a trailing newline on file output."""
    if dest:
        with Path(dest).open("w") as f:
            f.write(output)
            if not output.endswith("\n"):
                f.write("\n")
    else:
        typer.echo(output)


def _read_text(input_path: str | None) -> str | None:
    """Read text from a path, stdin (`-`), or omitted (stdin). None = empty TTY."""
    if not input_path or input_path == "-":
        if sys.stdin.isatty():
            return None
        return sys.stdin.read()
    return Path(input_path).read_text()


def _read_bytes(input_path: str | None) -> bytes | None:
    """Read bytes from a path, stdin (`-`), or omitted (stdin). None = empty TTY."""
    if not input_path or input_path == "-":
        if sys.stdin.isatty():
            return None
        return sys.stdin.buffer.read()
    return Path(input_path).read_bytes()


def convert(
    input: Annotated[  # noqa: A002 - matches the user-facing argument name
        str | None,
        typer.Argument(help="Input file. Use '-' or omit to read stdin."),
    ] = None,
    rejcl: Annotated[
        bool,
        typer.Option("--rejcl", help="Reverse mode: read a yaml/json/csv Job dump and emit JCL."),
    ] = False,
    from_fmt: Annotated[
        InputFormat | None,
        typer.Option("--from", help="Input format for --rejcl (auto-detected if omitted)."),
    ] = None,
    to: Annotated[
        OutputFormat,
        typer.Option("--to", help="Output format. zoau/mvscmd require the [zoau] extra."),
    ] = OutputFormat.json,
    output: Annotated[
        str | None,
        typer.Option("-o", "--output", help="Output file (default: stdout)."),
    ] = None,
    strict: Annotated[
        bool,
        typer.Option("--strict/--no-strict", help="Exit non-zero on validation warnings."),
    ] = True,
) -> None:
    """Parse IBM z/OS JCL and serialize to JSON, YAML, CSV, or roundtrip JCL."""
    if rejcl:
        text = _read_text(input)
        if text is None:
            raise typer.Exit(code=2)
        from fromjcl import rejcl as rejcl_mod

        try:
            result = rejcl_mod.convert(text, from_fmt.value if from_fmt else None)
        except (ValueError, KeyError) as e:
            typer.echo(f"Error: {e}", err=True)
            raise typer.Exit(code=1) from e
        _write_output(result, output)
        return

    try:
        if not input or input == "-":
            data = _read_bytes(input)
            if data is None:
                raise typer.Exit(code=2)
            parsed = parse_bytes(data)
        else:
            parsed = parse(input)
    except RuntimeError as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(code=1) from e

    warnings: list[str] = []
    if to == OutputFormat.raw:
        result = raw_out.convert(parsed)
    elif to == OutputFormat.json:
        result = json_out.convert(Job.from_parsed(parsed))
    elif to == OutputFormat.yaml:
        result = yaml_out.convert(Job.from_parsed(parsed))
    elif to == OutputFormat.csv:
        result = csv_out.convert(Job.from_parsed(parsed))
    elif to == OutputFormat.jcl:
        result = jcl_out.convert(parsed)
    elif to in _ZOAU_FORMATS:
        _require_extra("zoau", "bashlex")
        from fromjcl import _validate
        from fromjcl.converters.shell import mvscmd, zoau

        job = Job.from_parsed(parsed)
        result = (mvscmd if to == OutputFormat.mvscmd else zoau).convert(job)
        warnings = _validate.validate_shell(result)
        result = _validate.prepend_warnings(result, warnings, comment_prefix="#")
    else:  # pragma: no cover - Enum exhaustiveness; defensive default.
        result = ""

    _write_output(result, output)

    if warnings:
        typer.echo(f"fromjcl: validation failed ({len(warnings)} issue(s)):", err=True)
        for w in warnings:
            typer.echo(f"  - {w}", err=True)
        if strict:
            raise typer.Exit(code=1)


def main() -> int:
    """Console-script entry point. Returns an int exit code."""
    try:
        typer.run(convert)
    except SystemExit as e:
        code = e.code
        if isinstance(code, int):
            return code
        return 0 if code is None else 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
