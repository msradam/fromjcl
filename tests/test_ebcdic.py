# SPDX-License-Identifier: Apache-2.0
"""EBCDIC encoding support tests."""

from __future__ import annotations

from fromjcl.parser import parse_bytes

_MINIMAL_JCL = "//TESTJOB  JOB (ACCT),'TESTER',CLASS=A\n//STEP01   EXEC PGM=IEFBR14\n"


def test_ebcdic_auto_detect_variable_length() -> None:
    """EBCDIC cp037 bytes with NL separator are auto-detected and parsed."""
    ebcdic = _MINIMAL_JCL.encode("cp037")
    result = parse_bytes(ebcdic)
    stmts = result["statements"]
    assert len(stmts) >= 2
    assert stmts[0]["type"] == "JOB"
    assert stmts[0]["name"] == "TESTJOB"
    assert stmts[1]["type"] == "EXEC"


def test_ebcdic_auto_detect_fixed_length() -> None:
    """EBCDIC JCL as fixed 80-byte records (no newline) is auto-detected."""
    line = "//TESTJOB  JOB (ACCT),'TESTER',CLASS=A".ljust(80)
    ebcdic = line.encode("cp037")
    assert len(ebcdic) == 80
    result = parse_bytes(ebcdic)
    stmts = result["statements"]
    assert stmts[0]["type"] == "JOB"
    assert stmts[0]["name"] == "TESTJOB"


def test_ebcdic_explicit_cp037() -> None:
    """Explicit encoding='cp037' works."""
    ebcdic = _MINIMAL_JCL.encode("cp037")
    result = parse_bytes(ebcdic, encoding="cp037")
    assert result["statements"][0]["type"] == "JOB"


def test_ebcdic_explicit_cp500() -> None:
    """Explicit encoding='cp500' works."""
    ebcdic = _MINIMAL_JCL.encode("cp500")
    result = parse_bytes(ebcdic, encoding="cp500")
    assert result["statements"][0]["type"] == "JOB"


def test_ebcdic_cp1047_alias() -> None:
    """'cp1047' remaps to cp037 (identical for all JCL characters)."""
    # cp037 and cp1047 have the same byte values for every character used in JCL.
    ebcdic = _MINIMAL_JCL.encode("cp037")
    result = parse_bytes(ebcdic, encoding="cp1047")
    assert result["statements"][0]["type"] == "JOB"


def test_ebcdic_alias() -> None:
    """'ebcdic' alias resolves to cp037."""
    ebcdic = _MINIMAL_JCL.encode("cp037")
    result = parse_bytes(ebcdic, encoding="ebcdic")
    assert result["statements"][0]["type"] == "JOB"


def test_latin1_still_works_with_explicit_encoding() -> None:
    """Non-EBCDIC path with explicit 'latin-1' still parses correctly."""
    latin1 = _MINIMAL_JCL.encode("latin-1")
    result = parse_bytes(latin1, encoding="latin-1")
    assert result["statements"][0]["type"] == "JOB"
