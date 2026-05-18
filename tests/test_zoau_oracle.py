"""ZOAU oracle: assert our `--to zoau` converter emits the same canonical
ZOAU verb that IBM publishes alongside each example JCL.

Each `tests/jcl_samples/*.zoau` holds the first ZOAU command line shown on
the corresponding IBM topic page. We extract the verb (first whitespace
token, e.g. `mrm`, `dgrep`) and assert it appears in our converter's output.

This is a coarse check. Argument differences are tolerated, since IBM uses
`${prefix}` placeholders while our JCL uses `@@HLQ@@` literals. The verb
match is the load-bearing assertion.
"""

from pathlib import Path

import pytest

pytest.importorskip("bashlex", reason="zoau extra not installed")

from fromjcl.converters.shell import zoau  # noqa: E402
from fromjcl.models import Job  # noqa: E402
from fromjcl.parser import parse  # noqa: E402

SAMPLES = Path(__file__).parent / "jcl_samples"


def _verb(zoau_text: str) -> str:
    return zoau_text.strip().split()[0]


def _samples_with_oracles() -> list[tuple[Path, Path]]:
    pairs = []
    for jcl in sorted(SAMPLES.rglob("*.jcl")):
        oracle = jcl.with_suffix(".zoau")
        if oracle.exists():
            pairs.append((jcl, oracle))
    return pairs


@pytest.mark.parametrize(
    "jcl,oracle",
    _samples_with_oracles(),
    ids=lambda p: p.stem if isinstance(p, Path) else str(p),
)
def test_zoau_converter_emits_canonical_verb(jcl: Path, oracle: Path) -> None:
    job = Job.from_parsed(parse(str(jcl)))
    actual = zoau.convert(job)
    expected_verb = _verb(oracle.read_text())
    actual_lines = [ln for ln in actual.splitlines() if ln and not ln.startswith("#")]
    actual_verbs = {ln.split()[0] for ln in actual_lines if ln.split()}
    assert expected_verb in actual_verbs, (
        f"{jcl.name}: expected ZOAU verb '{expected_verb}' "
        f"(per IBM doc), got verbs {sorted(actual_verbs)}\n"
        f"--- our output ---\n{actual}"
    )
