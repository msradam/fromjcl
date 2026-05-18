# SPDX-License-Identifier: Apache-2.0
"""Unit tests for the model factory methods: Disposition.parse,
Space.parse, DCB.parse. Covers the empty/malformed/referback branches
the corpus-driven tests don't hit directly.
"""

from __future__ import annotations

from fromjcl.models import DCB, Disposition, Space


class TestDispositionParse:
    def test_none_defaults_to_shr(self) -> None:
        d = Disposition.parse(None)
        assert d.status == "SHR"
        assert d.normal is None
        assert d.abnormal is None

    def test_empty_string_defaults_to_shr(self) -> None:
        assert Disposition.parse("").status == "SHR"

    def test_single_status(self) -> None:
        d = Disposition.parse("OLD")
        assert (d.status, d.normal, d.abnormal) == ("OLD", None, None)

    def test_parenthesised_full_triple(self) -> None:
        d = Disposition.parse("(NEW,CATLG,DELETE)")
        assert (d.status, d.normal, d.abnormal) == ("NEW", "CATLG", "DELETE")

    def test_parenthesised_status_plus_normal(self) -> None:
        d = Disposition.parse("(MOD,PASS)")
        assert (d.status, d.normal, d.abnormal) == ("MOD", "PASS", None)

    def test_leading_comma_means_default_status(self) -> None:
        d = Disposition.parse("(,DELETE)")
        assert d.status == "SHR"
        assert d.normal == "DELETE"


class TestSpaceParse:
    def test_none_returns_none(self) -> None:
        assert Space.parse(None) is None

    def test_empty_returns_none(self) -> None:
        assert Space.parse("") is None

    def test_unparseable_returns_none(self) -> None:
        assert Space.parse("garbage") is None

    def test_primary_only(self) -> None:
        s = Space.parse("(TRK,10)")
        assert s is not None
        assert (s.type, s.primary, s.secondary, s.directory) == ("TRK", 10, None, None)

    def test_primary_secondary(self) -> None:
        s = Space.parse("(CYL,(5,2))")
        assert s is not None
        assert (s.type, s.primary, s.secondary) == ("CYL", 5, 2)

    def test_full_triple_with_directory(self) -> None:
        s = Space.parse("(TRK,(100,10,5))")
        assert s is not None
        assert (s.type, s.primary, s.secondary, s.directory) == ("TRK", 100, 10, 5)


class TestDCBParse:
    def test_none_returns_none(self) -> None:
        assert DCB.parse(None) is None

    def test_referback_returns_none(self) -> None:
        """`*.STEP.DD` references resolve at runtime; parser can't honour them."""
        assert DCB.parse("*.STEP1.SYSUT1") is None

    def test_single_attribute(self) -> None:
        d = DCB.parse("RECFM=FB")
        assert d is not None
        assert d.recfm == "FB"
        assert d.lrecl is None

    def test_parenthesised_multiple(self) -> None:
        d = DCB.parse("(RECFM=FB,LRECL=80,BLKSIZE=800)")
        assert d is not None
        assert (d.recfm, d.lrecl, d.blksize) == ("FB", 80, 800)

    def test_dsorg_picked_up(self) -> None:
        d = DCB.parse("DSORG=PO")
        assert d is not None
        assert d.dsorg == "PO"

    def test_non_numeric_lrecl_drops_silently(self) -> None:
        """Malformed numeric fields fall back to None rather than raising."""
        d = DCB.parse("LRECL=abc")
        assert d is None

    def test_all_unrecognised_returns_none(self) -> None:
        assert DCB.parse("FOO=BAR") is None
