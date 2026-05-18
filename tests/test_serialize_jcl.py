"""Test JCL serialization, especially PARM apostrophe escaping."""

from fromjcl.serialize.jcl import convert


def test_parm_with_single_apostrophe():
    """Single apostrophes in PARM values must be doubled in JCL output."""
    ir = {
        "statements": [
            {
                "type": "JOB",
                "name": "TEST",
                "parameters": [{"key": "CLASS", "value": "A"}],
            },
            {
                "type": "EXEC",
                "name": "S1",
                "parameters": [
                    {"key": "PGM", "value": "BPXBATCH"},
                    {"key": "PARM", "value": "SH echo 'hello'"},
                ],
            },
        ]
    }
    output = convert(ir)
    assert "PARM='SH echo ''hello'''" in output


def test_parm_with_no_apostrophe():
    """PARM values without apostrophes should work unchanged."""
    ir = {
        "statements": [
            {
                "type": "JOB",
                "name": "TEST",
                "parameters": [{"key": "CLASS", "value": "A"}],
            },
            {
                "type": "EXEC",
                "name": "S1",
                "parameters": [
                    {"key": "PGM", "value": "IEFBR14"},
                    {"key": "PARM", "value": "EP=MAIN"},
                ],
            },
        ]
    }
    output = convert(ir)
    assert "PARM='EP=MAIN'" in output


def test_parm_with_multiple_apostrophes():
    """Multiple apostrophes in PARM values must all be doubled."""
    ir = {
        "statements": [
            {
                "type": "JOB",
                "name": "TEST",
                "parameters": [{"key": "CLASS", "value": "A"}],
            },
            {
                "type": "EXEC",
                "name": "S1",
                "parameters": [
                    {"key": "PGM", "value": "BPXBATCH"},
                    {"key": "PARM", "value": "SH echo 'a' 'b'"},
                ],
            },
        ]
    }
    output = convert(ir)
    assert "PARM='SH echo ''a'' ''b'''" in output


def test_parm_already_quoted():
    """PARM values that are already quoted should have content escaped."""
    ir = {
        "statements": [
            {
                "type": "JOB",
                "name": "TEST",
                "parameters": [{"key": "CLASS", "value": "A"}],
            },
            {
                "type": "EXEC",
                "name": "S1",
                "parameters": [
                    {"key": "PGM", "value": "BPXBATCH"},
                    {"key": "PARM", "value": "'SH echo 'hello''"},
                ],
            },
        ]
    }
    output = convert(ir)
    # The inner apostrophes should be doubled
    assert "PARM='SH echo ''hello'''" in output
