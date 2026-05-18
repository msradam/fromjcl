"""Combinatoric roundtrip matrix: JCL → {IR, JSON, YAML, CSV} → JCL → IR.

The strongest fidelity yardstick for the parser + serializers + reverse
path together. The flow is:

    Job_before = Job.from_parsed(parse(jcl))
    text       = serialize(Job_before)             # one of json/yaml/csv
    jcl_again  = rejcl.convert(text)               # text → JCL bytes
    Job_after  = Job.from_parsed(parse(jcl_again))
    assert Job_before == Job_after                 # dataclass equality

Dataclass equality is structural: every Job/Step/DD/Dataset/DCB/Space/
Disposition field must match. Only the IR-level shape is checked —
byte-exact JCL roundtrip lives in test_parser_roundtrip.py (json/yaml/csv
inherently lose column metadata, comments, and trailing whitespace).

Scope:
- ibm/, community/, zoau/ samples — real-world JCL the IR is meant to model
- parser_edge_cases/ samples are SKIPPED: they exercise parser corner
  cases (inline DDs, hex INCLUDE, OUTPUT statements, etc.) the lossy IR
  is not designed to roundtrip through. The byte-exact parser test
  covers those.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from fromjcl import rejcl
from fromjcl.models import Job
from fromjcl.parser import parse
from fromjcl.serialize import csv as csv_out
from fromjcl.serialize import json as json_out
from fromjcl.serialize import yaml as yaml_out

SAMPLES = Path(__file__).parent / "jcl_samples"
ROUNDTRIPPABLE = sorted(
    p for p in SAMPLES.rglob("*.jcl") if p.parent.name in {"ibm", "community", "zoau"}
)

FORMATS = [
    ("json", json_out.convert),
    ("yaml", yaml_out.convert),
    ("csv", csv_out.convert),
]

# Known limitations of the rejcl path. Each entry maps a (format, sample
# stem) pair to the reason the roundtrip can't be a fixed point yet.
# Listed explicitly so a regression here surfaces — and so the failure
# inventory is visible to anyone scanning the test file.
_REJCL_XFAIL: dict[tuple[str, str], str] = {
    # Samples that exercise IF/THEN/ELSE: rejcl flattens nested IFs into
    # composite "(A) AND (NOT B)" condition strings that overflow the
    # JCL 71-column line limit. The serializer's IF emitter does not yet
    # break long conditions into continuation records, so the re-emitted
    # JCL is unparseable. Fix is in serialize/jcl.py:_emit_if.
    ("json", "if_nested_procs"): "IF re-emission exceeds 71-col limit",
    ("yaml", "if_nested_procs"): "IF re-emission exceeds 71-col limit",
    ("csv", "if_nested_procs"): "IF re-emission exceeds 71-col limit",
    # PARM= values with parenthesised lists and embedded quoted
    # tokens (e.g. PARM=(OBJECT,NODECK,'LINECOUNT=60')) round-trip
    # through serialize/jcl.py:_format_param, which doubles inner
    # apostrophes for JCL escape conventions. The serializer's PARM
    # escaping logic over-doubles when the value already has the
    # JCL-escaped form coming back through rejcl.
    ("json", "asm_lked_go_cond"): "PARM with paren-list + quoted token over-escapes",
    ("yaml", "asm_lked_go_cond"): "PARM with paren-list + quoted token over-escapes",
    ("csv", "asm_lked_go_cond"): "PARM with paren-list + quoted token over-escapes",
    # CSV is tabular and has no column for job-level SET symbols, so
    # samples that declare symbols lose them on the CSV roundtrip.
    # Fix is to either add a symbols column, emit a synthetic pre-row,
    # or document the limitation.
    ("csv", "grs87"): "CSV format drops job-level SET symbols",
    ("csv", "smf84fmt"): "CSV format drops job-level SET symbols",
    ("csv", "bcpii_hwirstcx_compile_bind"): "CSV format drops job-level SET symbols",
    ("csv", "gam_pli_cics_csdup"): "CSV format drops job-level SET symbols",
    ("csv", "gam_pli_db2_drop_tables"): "CSV format drops job-level SET symbols",
    ("csv", "kafka_ixyjrpa6_producer"): "CSV format drops job-level SET symbols",
    ("csv", "zopeneditor_asm_compile_link_run"): "CSV format drops job-level SET symbols",
    ("csv", "zowe_apilayer_racf_passticket"): "CSV format drops job-level SET symbols",
    ("csv", "zopeneditor_allocate"): "CSV format drops job-level SET symbols",
    ("csv", "zopeneditor_asmalloc"): "CSV format drops job-level SET symbols",
    ("csv", "zopeneditor_include_member"): "CSV format drops job-level SET symbols",
    ("csv", "zopeneditor_plialloc"): "CSV format drops job-level SET symbols",
    ("csv", "zopeneditor_rexalloc"): "CSV format drops job-level SET symbols",
    ("csv", "zopeneditor_run"): "CSV format drops job-level SET symbols",
}


def _parse_jcl_text(text: str) -> Job:
    tmp = tempfile.NamedTemporaryFile("w", suffix=".jcl", encoding="latin-1", delete=False)
    tmp.write(text)
    tmp.close()
    return Job.from_parsed(parse(tmp.name))


@pytest.mark.parametrize("jcl", ROUNDTRIPPABLE, ids=lambda p: str(p.relative_to(SAMPLES)))
@pytest.mark.parametrize("fmt,serialize", FORMATS, ids=[f[0] for f in FORMATS])
def test_roundtrip_via_format_preserves_ir(
    jcl: Path,
    fmt: str,
    serialize,
) -> None:
    """Job → format → JCL → Job must be a fixed point (dataclass equality)."""
    xfail_reason = _REJCL_XFAIL.get((fmt, jcl.stem))
    if xfail_reason:
        pytest.xfail(xfail_reason)

    job_before = Job.from_parsed(parse(str(jcl)))
    text = serialize(job_before)
    jcl_again = rejcl.convert(text, fmt)
    job_after = _parse_jcl_text(jcl_again)

    assert job_after == job_before, (
        f"{jcl.relative_to(SAMPLES)} via {fmt}: roundtrip altered the Job IR"
    )
