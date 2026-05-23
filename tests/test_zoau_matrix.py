"""Matrix test for the [zoau] extra: every JCL sample must produce
bashlex-clean zoau output and non-empty mvscmd output.

Catches cross-cutting regressions where a single converter's behaviour
silently degrades while its dedicated tests still pass.
"""

from __future__ import annotations

from pathlib import Path

import pytest

pytest.importorskip("bashlex", reason="zoau extra not installed")

from fromjcl import _validate  # noqa: E402
from fromjcl.converters.shell import mvscmd  # noqa: E402
from fromjcl.converters.shell import zoau as zoau_conv  # noqa: E402
from fromjcl.models import Job  # noqa: E402
from fromjcl.parser import parse  # noqa: E402

SAMPLES = Path(__file__).parent / "jcl_samples"
ALL = sorted(SAMPLES.rglob("*.jcl"))


@pytest.mark.parametrize("jcl", ALL, ids=lambda p: str(p.relative_to(SAMPLES)))
def test_zoau_and_mvscmd_handle_every_sample(jcl: Path) -> None:
    """Per-sample matrix: zoau output must validate clean, mvscmd must be non-empty."""
    job = Job.from_parsed(parse(str(jcl)))
    if not job.steps:
        pytest.skip(f"{jcl.name}: no executable steps (SET-only or config-only JCL)")



    # ZOAU shell: must parse as bash, every flag documented.
    zoau_out = zoau_conv.convert(job)
    zoau_warnings = _validate.validate_shell(zoau_out)
    assert not zoau_warnings, f"{jcl.name}: zoau output failed validation: {zoau_warnings}"

    # mvscmd shell: non-empty.
    mvscmd_out = mvscmd.convert(job)
    assert mvscmd_out.strip(), f"{jcl.name}: mvscmd empty"
