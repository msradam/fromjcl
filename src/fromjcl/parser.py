"""JCL parser entry point.

Single function, parse(path), returns the complete scan tree. Field
shape matches the C scanner in parser/src/scanjcl.c byte-for-byte: every
statement carries the column metadata and raw record bytes needed for
byte-exact roundtrip via serialize.jcl.convert.
"""

from typing import Any

from fromjcl._scanner import parse as _parse


def parse(path: str) -> dict[str, Any]:
    """Return the full parse tree (statements with column metadata + raw records)."""
    return _parse(path)
