"""Foundational output formats. No extras required, no classifier involved.

These serialisers dump the parse tree (or its Job model) without
interpreting JCL semantics. Compare with fromjcl/converters/, which
classify each step and translate it into a different ecosystem.
"""

from typing import Any


def remove_nulls(obj: object) -> object:
    """Recursively drop dict keys whose values are None, False, or empty dicts.
    Also rstrips trailing whitespace on instream fields, which the parser
    preserves for byte-exact roundtrip but is noise in human output."""
    if isinstance(obj, dict):
        cleaned: dict[str, Any] = {}
        for k, v in obj.items():
            if k == "instream" and isinstance(v, str):
                v = "\n".join(line.rstrip() for line in v.split("\n")).rstrip("\n")
            cleaned_v = remove_nulls(v)
            if cleaned_v is None or cleaned_v is False:
                continue
            cleaned[k] = cleaned_v
        return cleaned or None
    elif isinstance(obj, list):
        return [remove_nulls(item) for item in obj]
    return obj
