"""End-to-end matrix test: every sample must parse, model, roundtrip,
and serialize cleanly to every published format.
"""

from __future__ import annotations

import csv as csv_mod
import io
import json as json_mod
from pathlib import Path

import pytest
import yaml as yaml_mod

from fromjcl.models import Job
from fromjcl.parser import parse
from fromjcl.serialize import csv as csv_converter
from fromjcl.serialize import jcl as jcl_converter
from fromjcl.serialize import json as json_converter
from fromjcl.serialize import yaml as yaml_converter

SAMPLES = Path(__file__).parent / "jcl_samples"
ALL = sorted(SAMPLES.rglob("*.jcl"))


@pytest.mark.parametrize("jcl", ALL, ids=lambda p: str(p.relative_to(SAMPLES)))
def test_every_serializer_handles_every_sample(jcl: Path) -> None:
    """Per-sample matrix: every serializer must produce sensible output."""
    narrow = parse(str(jcl))
    full = parse(str(jcl))
    job = Job.from_parsed(narrow)

    assert job.steps, f"{jcl.name}: parser produced no steps"

    emitted = jcl_converter.convert(full)
    original = jcl.read_text(encoding="latin-1")
    assert emitted == original, f"{jcl.name}: --to jcl drifted from original"

    json_out = json_converter.convert(job)
    parsed_json = json_mod.loads(json_out)
    assert parsed_json.get("steps"), f"{jcl.name}: json missing steps"

    yaml_out = yaml_converter.convert(job)
    parsed_yaml = yaml_mod.safe_load(yaml_out)
    assert parsed_yaml.get("steps"), f"{jcl.name}: yaml missing steps"

    csv_out = csv_converter.convert(job)
    rows = list(csv_mod.DictReader(io.StringIO(csv_out)))
    assert csv_out.strip(), f"{jcl.name}: csv empty"
    for row in rows:
        assert row.get("step"), f"{jcl.name}: csv row missing step name"
