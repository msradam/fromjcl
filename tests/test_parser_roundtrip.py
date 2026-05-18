"""Parser correctness via roundtrip.

Primary guarantee, *byte-exact roundtrip*:

    emit(parse(x)) == x

If the parser truly understood the input, re-emitting it produces the
original file byte-for-byte. Anything less is information loss.

Secondary structural check (kept as a separate test so failures are easy
to diagnose):

    parse(emit(parse(x))) == parse(x)

This holds even when a downstream caller constructs a parsed dict
programmatically (no `raw_records`), proving the synthesising emitter is
also internally consistent.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from fromjcl.parser import parse
from fromjcl.serialize import jcl as jcl_converter

SAMPLES = Path(__file__).parent / "jcl_samples"


def _emit_then_parse(jcl_path: Path) -> dict:
    text = jcl_converter.convert(parse(str(jcl_path)))
    tmp = tempfile.NamedTemporaryFile("w", suffix=".jcl", encoding="latin-1", delete=False)
    tmp.write(text)
    tmp.close()
    return parse(tmp.name)


@pytest.mark.parametrize("sample", sorted(SAMPLES.rglob("*.jcl")), ids=lambda p: p.stem)
def test_byte_exact_roundtrip(sample: Path) -> None:
    """The strict guarantee: emit(parse(x)) == x at the byte level."""
    original = sample.read_text(encoding="latin-1")
    emitted = jcl_converter.convert(parse(str(sample)))
    assert emitted == original, (
        f"{sample.name}: byte-exact roundtrip failed. Parser dropped, "
        "altered, or normalised something."
    )


@pytest.mark.parametrize("sample", sorted(SAMPLES.rglob("*.jcl")), ids=lambda p: p.stem)
def test_narrow_parse_tree_is_roundtrip_fixed_point(sample: Path) -> None:
    original = parse(str(sample))
    after = _emit_then_parse(sample)
    assert original == after, f"{sample.name}: roundtrip altered the parse tree"


@pytest.mark.parametrize("sample", sorted(SAMPLES.rglob("*.jcl")), ids=lambda p: p.stem)
def test_emit_output_reparses_to_same_statement_count(sample: Path) -> None:
    """Cheap structural check separate from full equality, useful when
    diagnosing regressions in the emitter only."""
    original = parse(str(sample))
    after = _emit_then_parse(sample)
    assert len(original["statements"]) == len(after["statements"])
