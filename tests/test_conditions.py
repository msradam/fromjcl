"""JCL IF/THEN/ELSE → shell ``(( ... ))`` translation.

The parser composes IF/THEN/ELSE into ``Step.condition`` strings. The
translator lives in ``fromjcl.converters._conditions``. End-to-end tests
exercise the full path: JCL → parse → Job → zoau converter → output text.
"""

from __future__ import annotations

import tempfile
import textwrap

import pytest

pytest.importorskip("bashlex", reason="zoau extra not installed")

from fromjcl.converters import _conditions  # noqa: E402
from fromjcl.converters.shell import zoau  # noqa: E402
from fromjcl.models import Job  # noqa: E402
from fromjcl.parser import parse  # noqa: E402


def _parse_text(jcl_text: str) -> Job:
    tmp = tempfile.NamedTemporaryFile("w", suffix=".jcl", encoding="latin-1", delete=False)
    tmp.write(jcl_text)
    tmp.close()
    return Job.from_parsed(parse(tmp.name))


# ---------------------------------------------------------------------------
# Unit tests for the translator
# ---------------------------------------------------------------------------


def test_shell_simple_rc_eq():
    assert _conditions.to_shell("STEP01.RC = 0") == "step01_rc == 0"


def test_shell_word_op_le():
    assert _conditions.to_shell("STEP01.RC LE 4") == "step01_rc <= 4"


def test_shell_not_negation():
    assert _conditions.to_shell("NOT (STEP01.RC = 0)") == "! (step01_rc == 0)"


def test_shell_unicode_negation():
    # `¬STEP01.RUN` → `!1` (bash arithmetic accepts `!` without a space).
    assert _conditions.to_shell("¬STEP01.RUN") == "!1"


def test_shell_compound_and():
    expr = _conditions.to_shell("(STEP01.RC = 0) AND (STEP02.RC LE 4)")
    assert expr == "(step01_rc == 0) && (step02_rc <= 4)"


def test_shell_or_with_pipe():
    expr = _conditions.to_shell("STEP01.RC=0 | STEP02.RC=4")
    assert expr == "step01_rc == 0 || step02_rc == 4"


def test_shell_procstep_reference():
    """JCL form `EXP1.PSTEPONE.RC` → flattened to `exp1_pstepone_rc`."""
    expr = _conditions.to_shell("EXP1.PSTEPONE.RC > 4")
    assert "exp1_pstepone_rc" in expr
    assert ">" in expr


def test_warning_for_abend():
    assert _conditions._approx_warning("STEP01.ABEND") is not None


def test_warning_for_run():
    assert _conditions._approx_warning("¬STEP01.RUN") is not None


def test_no_warning_for_plain_rc():
    assert _conditions._approx_warning("STEP01.RC = 0") is None


# ---------------------------------------------------------------------------
# End-to-end: full JCL → zoau converter output
# ---------------------------------------------------------------------------


IF_ELSE = textwrap.dedent("""\
    //IFJOB    JOB (ACCT),'IF',CLASS=A
    //STEP01   EXEC PGM=IEFBR14
    //         IF (STEP01.RC = 0) THEN
    //STEP02   EXEC PGM=IEFBR14
    //         ELSE
    //STEP03   EXEC PGM=IEFBR14
    //         ENDIF
    """)


def test_zoau_emits_if_guard():
    job = _parse_text(IF_ELSE)
    out = zoau.convert(job)
    # The conditional steps must be wrapped in `if (( ... ))`.
    assert "if (( (step01_rc == 0) )); then" in out
    assert "if (( ! ((step01_rc == 0)) )); then" in out
    # First step captures rc unconditionally for downstream use.
    assert "step01_rc=$?" in out


def test_zoau_output_still_valid_shell_with_conditions():
    """bashlex must still parse the output (the if/fi blocks)."""
    import bashlex

    job = _parse_text(IF_ELSE)
    out = zoau.convert(job)
    body = "\n".join(ln for ln in out.splitlines() if not ln.lstrip().startswith("#"))
    bashlex.parse(body)  # raises if invalid
