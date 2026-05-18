# SPDX-License-Identifier: Apache-2.0
"""Runtime validators for emitted ZOAU / mvscmd shell.

Returns a list of warning strings (empty = clean). The CLI prepends these
to the script as `# WARNING:` lines so a reviewer sees them before
running the output.

Validation uses bashlex, brought in by the optional `[zoau]` extra. If
bashlex is unavailable (base install) validate_shell returns no warnings
rather than erroring. The gate at CLI level is the load-bearing check.
"""

from __future__ import annotations

from typing import Any

from fromjcl._zoau_flags import FLAGS as _ZOAU_FLAGS

# Wrappers: their flag namespace isn't a ZOAU command's. Skip them.
_WRAPPER_VERBS = frozenset(
    {"mvscmd", "mvscmdauth", "echo", "tsocmd", "export", "awk", "sed", "cat"}
)


def _walk_commands(node: Any) -> list[list[str]]:
    """Word-token list of every command node in a bashlex tree."""
    out: list[list[str]] = []
    if getattr(node, "kind", None) == "command":
        out.append(
            [p.word for p in getattr(node, "parts", []) if getattr(p, "kind", None) == "word"]
        )
    for attr in ("parts", "commands", "list"):
        for child in getattr(node, attr, []) or []:
            out.extend(_walk_commands(child))
    return out


def _flag_tokens(words: list[str]) -> list[str]:
    # Skips numeric args (`-1`) and grouped shorts (`-rf`) since the manpage table lists neither.
    flags: list[str] = []
    for w in words[1:]:
        if w.startswith("--"):
            flags.append(w.split("=", 1)[0])
        elif w.startswith("-") and len(w) >= 2 and w[1].isalpha():
            flags.append(w[:2])
    return flags


def validate_shell(text: str) -> list[str]:
    """Validate ZOAU/mvscmd shell output. Returns warning strings."""
    try:
        import bashlex  # type: ignore[import-untyped]
    except ImportError:
        return []

    # Strip our own # banners before parsing; they can contain quotes that confuse bashlex.
    body = "\n".join(ln for ln in text.splitlines() if not ln.lstrip().startswith("#"))
    if not body.strip():
        return []

    warnings: list[str] = []
    try:
        trees = bashlex.parse(body)
    except Exception as exc:
        warnings.append(f"shell parse failed: {exc}")
        return warnings

    for tree in trees:
        for words in _walk_commands(tree):
            if not words:
                continue
            verb = words[0]
            if verb in _WRAPPER_VERBS or verb.startswith("/") or "=" in verb:
                continue
            documented = _ZOAU_FLAGS.get(verb)
            if documented is None:
                continue
            unknown = [f for f in _flag_tokens(words) if f not in documented]
            if unknown:
                warnings.append(f"{verb}: undocumented flag(s) {unknown}")
    return warnings


def prepend_warnings(text: str, warnings: list[str], comment_prefix: str) -> str:
    """Prepend # WARNING: ... lines to the output."""
    if not warnings:
        return text
    banner = f"{comment_prefix} fromjcl validation: {len(warnings)} issue(s)\n"
    header = "\n".join(f"{comment_prefix} WARNING: {w}" for w in warnings)
    return banner + header + "\n" + text
