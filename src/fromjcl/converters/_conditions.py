"""Translate JCL IF-condition strings to shell (( ... )) and Ansible when:.

STEP.ABEND approximates as rc != 0. STEP.RUN approximates as true.
STEP.ABENDCC=... approximates as rc != 0. Each approximation is flagged
via _approx_warning.
"""

from __future__ import annotations

import re
from typing import Any

# Replace word ops in *original* (uppercase) form before changing case.
_WORD_OPS = [
    (r"\bEQ\b", "=="),
    (r"\bNE\b", "!="),
    (r"\bLE\b", "<="),
    (r"\bGE\b", ">="),
    (r"\bLT\b", "<"),
    (r"\bGT\b", ">"),
]


def _normalise_ops(s: str) -> str:
    """Convert all comparison operators to C-style forms."""
    for pat, repl in _WORD_OPS:
        s = re.sub(pat, repl, s)
    s = s.replace("<>", "!=").replace("^=", "!=")
    # Bare = becomes == (avoid touching ==, !=, <=, >=).
    s = re.sub(r"(?<![=!<>])=(?!=)", "==", s)
    return s


def _step_ref_re() -> re.Pattern[str]:
    """Matches STEPNAME.{RC|ABEND|RUN|ABENDCC} *and* the procstep form
    PROCSTEP.SUBSTEP.{...} (where the JCL refers into a PROC's step)."""
    return re.compile(r"\b([A-Z][A-Z0-9$@#]*(?:\.[A-Z][A-Z0-9$@#]*)?)\.(RC|ABEND|RUN|ABENDCC)\b")


def _approx_warning(text: str) -> str | None:
    """Return a warning string if the condition uses constructs we can't
    faithfully translate."""
    if re.search(r"\.ABEND\b", text) or re.search(r"\.ABENDCC\b", text):
        return "ABEND condition approximated as non-zero RC"
    if re.search(r"\.RUN\b", text):
        return "RUN condition approximated as always-true"
    return None


def to_shell(jcl_cond: str) -> str:
    """Translate to a bash (( ... )) arithmetic expression body.

    The caller wraps with if (( ... )); then ... fi.
    """
    s = jcl_cond

    def _ref(m: re.Match[str]) -> str:
        # EXP1.PSTEPONE (procstep) becomes exp1_pstepone.
        name = m.group(1).lower().replace(".", "_")
        kind = m.group(2)
        if kind == "RC":
            return f"{name}_rc"
        if kind == "ABEND":
            return f"{name}_rc != 0"
        if kind == "RUN":
            # bash `(( 1 ))` evaluates truthy → "always run". A safe
            # approximation since we can't know at script-emit time
            # whether the referenced step actually executed.
            return "1"
        # ABENDCC=Uxxxx : approximate as non-zero; the literal that
        # follows the comparison is left in place so a reviewer can see
        # what was intended.
        return f"{name}_rc != 0 /* ABENDCC */"

    s = _step_ref_re().sub(_ref, s)
    s = _normalise_ops(s)

    s = re.sub(r"\bAND\b", "&&", s)
    s = re.sub(r"\bOR\b", "||", s)
    s = re.sub(r"\bNOT\b", "!", s)
    s = re.sub(r"(?<!&)&(?!&)", "&&", s)
    s = re.sub(r"(?<!\|)\|(?!\|)", "||", s)
    s = s.replace("¬", "!")
    # Tidy whitespace around binary ops for readability.
    s = re.sub(r"\s*(==|!=|<=|>=|<|>|&&|\|\|)\s*", r" \1 ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def to_ansible(jcl_cond: str) -> str:
    """Translate to a Jinja2-style when: expression."""
    s = jcl_cond

    def _ref(m: re.Match[str]) -> str:
        name = m.group(1).lower().replace(".", "_")
        kind = m.group(2)
        if kind == "RC":
            return f"{name}.rc"
        if kind == "ABEND":
            return f"{name}.failed"
        if kind == "RUN":
            return "true"
        # ABENDCC=Uxxxx : approximate; leave the literal alone so the
        # comparison still parses (will compare a bool to a string;
        # always false). Reviewer should see the warning comment.
        return f"{name}.failed"

    s = _step_ref_re().sub(_ref, s)
    s = _normalise_ops(s)

    s = re.sub(r"\bAND\b", "and", s)
    s = re.sub(r"\bOR\b", "or", s)
    s = re.sub(r"\bNOT\b", "not", s)
    s = re.sub(r"(?<!&)&(?!&)", " and ", s)
    s = re.sub(r"(?<!\|)\|(?!\|)", " or ", s)
    s = s.replace("¬", "not ")
    # Tidy whitespace around binary ops.
    s = re.sub(r"\s*(==|!=|<=|>=|<|>)\s*", r" \1 ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def shell_var(step_name: str) -> str:
    """Shell variable name holding the return code for step_name."""
    return f"{step_name.lower()}_rc"


def ansible_register(step_name: str) -> str:
    """Ansible register: variable name for the task result of step_name."""
    return step_name.lower()


def group_consecutive_by_condition[T](
    items: list[T],
) -> list[tuple[str | None, list[T]]]:
    """Group consecutive items sharing the same condition attribute."""
    groups: list[tuple[str | None, list[T]]] = []
    for item in items:
        cond = getattr(item, "condition", None)
        if groups and groups[-1][0] == cond:
            groups[-1][1].append(item)
        else:
            groups.append((cond, [item]))
    return groups


def referenced_step_names(items: list[Any]) -> set[str]:
    """Step names mentioned in any condition or cond, i.e. steps whose
    RC something downstream needs. Emitters use this to decide whether
    to capture <step>_rc=$?."""
    refs: set[str] = set()
    pattern = re.compile(r"\b([A-Z][A-Z0-9$@#]*)\.(RC|ABEND|RUN|ABENDCC)\b")
    for item in items:
        for attr in ("condition", "cond"):
            text = getattr(item, attr, None)
            if not text:
                continue
            for m in pattern.finditer(text):
                refs.add(m.group(1).split(".")[0].lower())
    return refs
