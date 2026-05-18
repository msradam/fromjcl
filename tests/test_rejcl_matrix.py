"""Combinatoric roundtrip matrix: JCL → {IR, JSON, YAML, CSV} → JCL → IR.

The strongest fidelity yardstick for the parser + serializers + reverse
path together. The flow is:

    Job_before = Job.from_parsed(parse(jcl))
    text       = serialize(Job_before)             # one of json/yaml/csv
    jcl_again  = rejcl.convert(text)               # text → JCL bytes
    Job_after  = Job.from_parsed(parse(jcl_again))
    assert Job_before == Job_after                 # dataclass equality

Dataclass equality is structural: every Job/Step/DD/Dataset/DCB/Space/
Disposition field must match. Only the IR-level shape is checked here.
Byte-exact JCL roundtrip lives in test_parser_roundtrip.py (json/yaml/csv
inherently lose column metadata, comments, and trailing whitespace).

Scope:
- ibm/, community/, zoau/ samples: real-world JCL the IR is meant to model
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

# Known limitations of the rejcl roundtrip. Empty: every sample in
# the ibm/community/zoau corpora round-trips through every format.
# Earlier entries were resolved by fixes in:
#   serialize/jcl.py        IF continuation, PARM paren-list passthrough
#   serialize/csv.py        symbols column, trailing blank line preserve
#   serialize/__init__.py   instream terminator-newline rule
_REJCL_XFAIL: dict[tuple[str, str], str] = {}


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
