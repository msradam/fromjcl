# SPDX-License-Identifier: Apache-2.0
"""JCL parser entry points.

parse(path) reads from disk; parse_bytes(data) takes a buffer directly
(stdin, network input, in-memory test fixtures). Both return the same
scan tree shape, matching the C scanner in parser/src/scanjcl.c
byte-for-byte: every statement carries the column metadata and raw
record bytes needed for byte-exact roundtrip via serialize.jcl.convert.
"""

from typing import Any

from fromjcl._scanner import parse as _parse
from fromjcl._scanner import parse_bytes as _parse_bytes


def parse(path: str) -> dict[str, Any]:
    """Return the full parse tree from a JCL file path."""
    return _parse(path)


def parse_bytes(data: bytes) -> dict[str, Any]:
    """Return the full parse tree from a JCL bytes buffer."""
    return _parse_bytes(data)
