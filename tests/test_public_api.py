# SPDX-License-Identifier: Apache-2.0
"""Locks in the public Python API. Adding or removing a top-level
export is a deliberate change; this test catches accidental drift."""

from __future__ import annotations

import fromjcl

EXPECTED = {
    "parse",
    "parse_bytes",
    "Job",
    "Step",
    "DD",
    "Dataset",
    "Disposition",
    "Space",
    "DCB",
    "to_json",
    "to_yaml",
    "to_csv",
    "to_jcl",
    "to_raw",
    "from_dump",
}


def test_all_matches_expected() -> None:
    assert set(fromjcl.__all__) == EXPECTED


def test_every_name_in_all_is_importable() -> None:
    for name in fromjcl.__all__:
        assert hasattr(fromjcl, name), f"{name} listed in __all__ but missing from module"


def test_all_listed_names_are_correctly_typed() -> None:
    """Sanity: every export resolves to either a class or a callable."""
    for name in fromjcl.__all__:
        obj = getattr(fromjcl, name)
        assert isinstance(obj, type) or callable(obj), f"{name} is neither a class nor callable"


def test_forward_path_works() -> None:
    """End-to-end: parse, build Job, serialize via each to_*."""
    from pathlib import Path

    sample = Path("tests/jcl_samples/zoau/create_data_set.jcl")
    parsed = fromjcl.parse(str(sample))
    job = fromjcl.Job.from_parsed(parsed)

    assert isinstance(fromjcl.to_json(job), str)
    assert isinstance(fromjcl.to_yaml(job), str)
    assert isinstance(fromjcl.to_csv(job), str)
    assert fromjcl.to_jcl(parsed) == sample.read_text(encoding="latin-1")
    assert isinstance(fromjcl.to_raw(parsed), str)


def test_reverse_path_works() -> None:
    from pathlib import Path

    sample = Path("tests/jcl_samples/zoau/create_data_set.jcl")
    job = fromjcl.Job.from_parsed(fromjcl.parse(str(sample)))
    yaml_text = fromjcl.to_yaml(job)
    jcl_again = fromjcl.from_dump(yaml_text, "yaml")
    assert "//" in jcl_again
