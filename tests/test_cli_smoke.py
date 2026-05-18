# SPDX-License-Identifier: Apache-2.0
"""End-to-end CLI smoke tests via subprocess.

The unit-level test in test_cli_gate.py monkeypatches sys.argv and
calls cli.main() directly, which can't catch entry-point wiring bugs
(missing [project.scripts] declaration, bad shebang, import errors at
load time). These tests spawn the installed `fromjcl` binary and check
the actual contract.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).parent.parent
SAMPLE = REPO_ROOT / "tests" / "jcl_samples" / "zoau" / "create_data_set.jcl"

FROMJCL = REPO_ROOT / ".venv" / "bin" / "fromjcl"
if not FROMJCL.exists():
    pytest.skip("fromjcl entry-point not installed in .venv", allow_module_level=True)


def _run(*args: str, stdin_bytes: bytes | None = None) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(
        [str(FROMJCL), *args],
        input=stdin_bytes,
        capture_output=True,
        timeout=15,
        check=False,
    )


def test_to_yaml_from_file_parses_back() -> None:
    result = _run(str(SAMPLE), "--to", "yaml")
    assert result.returncode == 0, result.stderr.decode()
    loaded = yaml.safe_load(result.stdout)
    assert isinstance(loaded, dict)
    assert loaded.get("steps"), "yaml output missing steps"


def test_to_json_from_file_parses_back() -> None:
    result = _run(str(SAMPLE), "--to", "json")
    assert result.returncode == 0, result.stderr.decode()
    loaded = json.loads(result.stdout)
    assert loaded.get("steps")


def test_to_jcl_is_byte_exact() -> None:
    result = _run(str(SAMPLE), "--to", "jcl")
    assert result.returncode == 0, result.stderr.decode()
    assert result.stdout.decode("latin-1").rstrip("\n") == SAMPLE.read_text(
        encoding="latin-1"
    ).rstrip("\n")


def test_stdin_input() -> None:
    """Bytes piped on stdin should parse like a file."""
    result = _run("--to", "json", stdin_bytes=SAMPLE.read_bytes())
    assert result.returncode == 0, result.stderr.decode()
    assert json.loads(result.stdout).get("steps")


def test_bad_format_exits_nonzero() -> None:
    result = _run(str(SAMPLE), "--to", "bogus")
    assert result.returncode != 0
    assert b"bogus" in result.stderr.lower() or b"invalid" in result.stderr.lower()


def test_help_runs() -> None:
    result = _run("--help")
    assert result.returncode == 0
    assert b"fromjcl" in result.stdout.lower() or b"usage" in result.stdout.lower()


def test_rejcl_via_subprocess(tmp_path: Path) -> None:
    """Forward then reverse via the actual entry point should produce
    parseable JCL."""
    forward = _run(str(SAMPLE), "--to", "json")
    assert forward.returncode == 0

    json_file = tmp_path / "job.json"
    json_file.write_bytes(forward.stdout)

    reverse = _run(str(json_file), "--rejcl", "--from", "json")
    assert reverse.returncode == 0, reverse.stderr.decode()
    assert b"//" in reverse.stdout, "rejcl output missing JCL prefix"
    assert sys.platform != "win32" or reverse.stdout.startswith(b"//")
