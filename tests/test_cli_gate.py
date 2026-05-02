"""CLI smoke: every published serializer format runs cleanly and exits 0."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from fromjcl import cli

SAMPLE = Path(__file__).parent / "jcl_samples" / "zoau" / "create_data_set.jcl"


@pytest.mark.parametrize("fmt", ["json", "yaml", "csv", "raw", "jcl"])
def test_serializer_formats_exit_zero(monkeypatch, capsys, fmt):
    """Every serializer output runs to completion and produces text."""
    monkeypatch.setattr(sys, "argv", ["fromjcl", str(SAMPLE), "--to", fmt])
    rc = cli.main()
    captured = capsys.readouterr()
    assert rc == 0, f"--to {fmt} should exit 0"
    assert captured.out.strip(), f"--to {fmt} produced no output"
