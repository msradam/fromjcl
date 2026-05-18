"""bashlex-based validator for the ZOAU shell emitter: clean output emits
no warnings; degenerate output emits informative warnings that the CLI
prepends to the script as `# WARNING:` lines.
"""

from __future__ import annotations

from pathlib import Path

import pytest

pytest.importorskip("bashlex", reason="zoau extra not installed")

from fromjcl import _validate  # noqa: E402
from fromjcl.converters.shell import zoau as zoau_conv  # noqa: E402
from fromjcl.models import Job  # noqa: E402
from fromjcl.parser import parse  # noqa: E402

SAMPLES = Path(__file__).parent / "jcl_samples"


def test_clean_zoau_output_emits_no_warnings():
    job = Job.from_parsed(parse(str(SAMPLES / "zoau" / "create_data_set.jcl")))
    out = zoau_conv.convert(job)
    assert _validate.validate_shell(out) == []


def test_invalid_shell_surfaces_parse_warning():
    # Unbalanced quote → bashlex parse fails.
    warnings = _validate.validate_shell('dtouch "unclosed string\n')
    assert warnings
    assert "shell parse failed" in warnings[0]


def test_undocumented_flag_surfaces_warning():
    # `dtouch` doesn't accept `--banana`.
    warnings = _validate.validate_shell('dtouch --banana "DSN"\n')
    assert warnings
    assert any("dtouch" in w and "--banana" in w for w in warnings)


def test_unknown_verb_does_not_warn():
    # No manpage for `randomscript` — silently skipped, not flagged.
    assert _validate.validate_shell("randomscript -x foo\n") == []


def test_prepend_warnings_adds_banner_and_lines():
    out = _validate.prepend_warnings("echo hello\n", ["thing went wrong"], comment_prefix="#")
    assert out.startswith("# fromjcl validation: 1 issue(s)")
    assert "# WARNING: thing went wrong" in out
    assert "echo hello" in out


def test_prepend_warnings_noop_when_clean():
    assert _validate.prepend_warnings("ok\n", [], comment_prefix="#") == "ok\n"
