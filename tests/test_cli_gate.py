"""The CLI must treat validation warnings as a fatal gate by default.

`--to zoau` (and `--to mvscmd`) runs `validate_shell` over its output via
bashlex + the frozen ZOAU manpage table. When the validator surfaces
issues, the CLI:
- still emits the output (with `# WARNING:` lines prepended) so the user
  can see what the converter tried to produce
- mirrors a summary to stderr
- exits non-zero by default; `--no-strict` overrides to exit 0
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

pytest.importorskip("bashlex", reason="zoau extra not installed")

from fromjcl import cli  # noqa: E402

SAMPLE = Path(__file__).parent / "jcl_samples" / "zoau" / "create_data_set.jcl"


def _run(monkeypatch, args, capsys, fake_warnings_shell=None):
    """Invoke cli.main() with stubbed argv. Optionally stub validate_shell
    so a test can simulate broken converter output without manufacturing
    JCL that would actually provoke a real warning."""
    monkeypatch.setattr(sys, "argv", ["fromjcl", *args])
    if fake_warnings_shell is not None:
        monkeypatch.setattr(
            "fromjcl._validate.validate_shell",
            lambda _: list(fake_warnings_shell),
        )
    rc = cli.main()
    captured = capsys.readouterr()
    return rc, captured.out, captured.err


def test_clean_zoau_conversion_exits_zero(monkeypatch, capsys):
    rc, out, err = _run(monkeypatch, [str(SAMPLE), "--to", "zoau"], capsys)
    assert rc == 0
    assert "dtouch" in out
    assert err == ""


def test_strict_zoau_conversion_with_warnings_exits_one(monkeypatch, capsys):
    rc, out, err = _run(
        monkeypatch,
        [str(SAMPLE), "--to", "zoau"],
        capsys,
        fake_warnings_shell=["dtouch: undocumented flag(s) ['--banana']"],
    )
    assert rc == 1, "strict mode must fail when validation warns"
    assert "# WARNING:" in out, "warnings still prepended to output"
    assert "validation failed (1 issue(s))" in err
    assert "--banana" in err


def test_no_strict_lets_warnings_pass(monkeypatch, capsys):
    rc, out, err = _run(
        monkeypatch,
        [str(SAMPLE), "--to", "zoau", "--no-strict"],
        capsys,
        fake_warnings_shell=["something fishy"],
    )
    assert rc == 0, "--no-strict downgrades validation failure to warning-only"
    assert "# WARNING:" in out
    # Still surfaced to stderr so the human running the command sees it.
    assert "validation failed" in err


def test_mvscmd_runs_through_the_same_gate(monkeypatch, capsys):
    """--to mvscmd shares the validate_shell gate with --to zoau."""
    rc, out, err = _run(
        monkeypatch,
        [str(SAMPLE), "--to", "mvscmd"],
        capsys,
        fake_warnings_shell=["mvscmd: ouch"],
    )
    assert rc == 1
    assert "# WARNING:" in out
    assert "ouch" in err


def test_non_validated_formats_never_gate(monkeypatch, capsys):
    """JSON / YAML / JCL / CSV output paths don't run a validator and
    therefore can't fail the gate, even with --strict (the default)."""
    for fmt in ["json", "yaml", "jcl", "csv"]:
        rc, out, _err = _run(monkeypatch, [str(SAMPLE), "--to", fmt], capsys)
        assert rc == 0, f"--to {fmt} should never gate"
        assert out.strip(), f"--to {fmt} produced no output"
