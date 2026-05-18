# SPDX-License-Identifier: Apache-2.0
"""Regression tests against golden JSON and YAML output for a curated
subset of JCL samples. Catches semantic drift the matrix tests miss
(field rename, value normalisation, ordering changes).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from fromjcl.models import Job
from fromjcl.parser import parse
from fromjcl.serialize import json as json_out
from fromjcl.serialize import yaml as yaml_out

SAMPLES = Path(__file__).parent / "jcl_samples"
JSON_GOLDEN = Path(__file__).parent / "json_samples"
YML_GOLDEN = Path(__file__).parent / "yml_samples"

GOLDEN_STEMS = sorted(
    {p.stem for p in JSON_GOLDEN.glob("*.json")} & {p.stem for p in YML_GOLDEN.glob("*.yml")}
)


def _find_jcl(stem: str) -> Path:
    matches = list(SAMPLES.rglob(f"{stem}.jcl"))
    if not matches:
        pytest.fail(f"no jcl_samples/**/{stem}.jcl for golden {stem}")
    if len(matches) > 1:
        pytest.fail(f"ambiguous jcl_samples for {stem}: {matches}")
    return matches[0]


def _normalize(text: str) -> str:
    """Compare with a single trailing newline so a POSIX-tidy golden file
    matches the raw convert() output regardless of which serializer
    happens to append one."""
    return text.rstrip("\n") + "\n"


@pytest.mark.parametrize("stem", GOLDEN_STEMS)
def test_json_matches_golden(stem: str) -> None:
    jcl = _find_jcl(stem)
    actual = json_out.convert(Job.from_parsed(parse(str(jcl))))
    expected = (JSON_GOLDEN / f"{stem}.json").read_text()
    assert _normalize(actual) == _normalize(expected), f"{stem}: json output drifted from golden"


@pytest.mark.parametrize("stem", GOLDEN_STEMS)
def test_yaml_matches_golden(stem: str) -> None:
    jcl = _find_jcl(stem)
    actual = yaml_out.convert(Job.from_parsed(parse(str(jcl))))
    expected = (YML_GOLDEN / f"{stem}.yml").read_text()
    assert _normalize(actual) == _normalize(expected), f"{stem}: yaml output drifted from golden"
