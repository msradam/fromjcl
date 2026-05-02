"""Dump the raw scanner output as JSON, including column metadata.

Useful for debugging the parser or feeding the full record-level detail
into another tool.
"""

import json
from typing import Any


def convert(parsed: dict[str, Any]) -> str:
    """Return the unmodified parse tree as indented JSON."""
    return json.dumps(parsed, indent=2)
