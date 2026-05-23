# SPDX-License-Identifier: Apache-2.0
"""Targeted regression tests for scanner and model bugs fixed in 0.4.0."""

from __future__ import annotations

from pathlib import Path

from fromjcl.models import Job
from fromjcl.parser import parse
from fromjcl.rejcl import convert as rejcl_convert
from fromjcl.serialize.json import convert as to_json

SAMPLES = Path(__file__).parent / "jcl_samples"


def test_col72_continuation_false_positive() -> None:
    """Content reaching column 72 must not set ContinueComment state.

    zna_copy.jcl has MSGCLASS=__MSGCLASS__ in the JOB card whose value
    fills to column 72. The scanner previously treated the next statement
    as a continued comment and raised ValueError.
    """
    path = SAMPLES / "ibm" / "zna_copy.jcl"
    job = Job.from_parsed(parse(str(path)))
    assert job.name == "COPY"
    assert len(job.steps) > 0


def test_lowercase_jobname_accepted() -> None:
    """Lowercase letters in a jobname must be accepted.

    Template JCL commonly uses lowercase placeholder characters (e.g.
    TKTabc1 where abc is replaced by a user suffix). The scanner
    previously rejected any non-uppercase alphabetic character.
    """
    path = SAMPLES / "parser_edge_cases" / "lowercase_jobname.jcl"
    job = Job.from_parsed(parse(str(path)))
    assert job.name == "TKTabc1"


def test_multi_element_account_preserved() -> None:
    """A parenthesised multi-element JOB account must not be split at commas.

    (ACCT001,BIN1,BLDG2,DEPT3) was previously truncated to (ACCT001
    because comma-splitting logic ran before paren-nesting was tracked.
    """
    path = SAMPLES / "parser_edge_cases" / "acct_multi_element.jcl"
    job = Job.from_parsed(parse(str(path)))
    assert job.account == "(ACCT001,BIN1,BLDG2,DEPT3)"


def test_custom_dlm_preserved_in_model() -> None:
    """DLM='@@' must survive the forward pass into the Job model."""
    path = SAMPLES / "parser_edge_cases" / "dlm_custom_delimiter.jcl"
    job = Job.from_parsed(parse(str(path)))
    dd = job.steps[0].dds[0]
    assert dd.instream is not None
    assert dd.instream_dlm == "@@"


def test_custom_dlm_roundtrip_via_json() -> None:
    """DLM='@@' must survive JSON serialisation and rejcl reconstruction."""
    path = SAMPLES / "parser_edge_cases" / "dlm_custom_delimiter.jcl"
    job = Job.from_parsed(parse(str(path)))
    roundtripped = rejcl_convert(to_json(job), "json")
    assert "DLM='@@'" in roundtripped
    assert "@@" in roundtripped
    assert "HELLO FROM INSTREAM" in roundtripped
