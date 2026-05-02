"""Roundtrip: emit JCL text from a parsed statement list."""

from collections.abc import Callable
from typing import Any

JCL_TXTLEN = 71
CONT_COL = 15


def _format_param(kvp: dict[str, Any]) -> str:
    key = kvp.get("key") or ""
    val = kvp.get("value")
    if val is None:
        return key
    return f"{key}={val}"


def _split_outside_quotes(body: str) -> list[str]:
    """Split on commas, but never break inside '...' or (...)."""
    parts: list[str] = []
    buf: list[str] = []
    in_quote = False
    paren = 0
    for c in body:
        if c == "'" and paren == 0:
            in_quote = not in_quote
            buf.append(c)
        elif c == "(" and not in_quote:
            paren += 1
            buf.append(c)
        elif c == ")" and not in_quote:
            paren -= 1
            buf.append(c)
        elif c == "," and not in_quote and paren == 0:
            parts.append("".join(buf))
            buf = []
        else:
            buf.append(c)
    parts.append("".join(buf))
    return parts


def _last_comma_within(seg: str, limit: int) -> int:
    """Index of the last comma in seg[:limit] that is at paren-depth zero
    (so we don't break a (...) by accident, but DO break between siblings
    inside one). Returns -1 if no eligible comma exists."""
    depth = 0
    last = -1
    for j, c in enumerate(seg[:limit]):
        if c == "(":
            depth += 1
        elif c == ")":
            depth -= 1
        elif c == "," and depth <= 1:
            last = j
    return last


def _emit_card(name: str, keyword: str, body: str) -> list[str]:
    """Emit a JCL card with the given name, keyword, and body. Wraps when the
    record exceeds 71 characters by breaking at parameter commas; continuation
    lines start at column 16 with a leading //."""
    name = name or ""
    prefix = f"//{name:<8} {keyword}"
    head = f"{prefix} " if body else prefix
    first = head + body
    if len(first) <= JCL_TXTLEN:
        return [first]

    parts = _split_outside_quotes(body)
    cont = "//" + " " * (CONT_COL - 2)
    lines: list[str] = []
    cur = head
    i = 0
    while i < len(parts):
        seg = parts[i]
        sep = "," if i + 1 < len(parts) else ""
        candidate = cur + seg + sep
        if len(candidate) <= JCL_TXTLEN:
            cur = candidate
            i += 1
        elif cur != head and cur != cont:
            # Wrap: close current line with trailing comma, start continuation.
            lines.append(cur if cur.endswith(",") else cur + ",")
            cur = cont
        else:
            # Single segment exceeds line; prefer to split at an internal
            # comma (depth-1 paren-list), else hard-split.
            avail = JCL_TXTLEN - len(cur)
            split = _last_comma_within(seg, avail)
            if split > 0:
                lines.append(cur + seg[: split + 1])  # include the comma
                parts[i] = seg[split + 1 :]
            elif avail > 0:
                lines.append(cur + seg[:avail])
                parts[i] = seg[avail:]
            else:
                lines.append(cur)
            cur = cont
    if cur != cont:
        lines.append(cur)
    return lines


def _emit_comment(stmt: dict[str, Any], name: str, params: list[dict[str, Any]]) -> list[str]:
    text = ""
    if stmt.get("scanned_lines"):
        text = (stmt["scanned_lines"][0].get("comment_text") or "").rstrip()
    elif params:
        text = (params[0].get("key") or "").rstrip()
    return [f"//*{text}"]


def _emit_jes2(stmt: dict[str, Any], name: str, params: list[dict[str, Any]]) -> list[str]:
    text = (params[0].get("key") or "").rstrip() if params else ""
    return [f"/*{text}"]


def _emit_if(stmt: dict[str, Any], name: str, params: list[dict[str, Any]]) -> list[str]:
    cond = stmt.get("conditional")
    if isinstance(cond, dict):
        cond = cond.get("text")
    cond_text = (cond or "").strip()
    if name:
        return [f"//{name:<8} IF {cond_text} THEN"]
    return [f"//          IF {cond_text} THEN"]


def _emit_else(stmt: dict[str, Any], name: str, params: list[dict[str, Any]]) -> list[str]:
    return [f"//{name:<8} ELSE"] if name else ["//          ELSE"]


def _emit_endif(stmt: dict[str, Any], name: str, params: list[dict[str, Any]]) -> list[str]:
    return [f"//{name:<8} ENDIF"] if name else ["//          ENDIF"]


def _emit_dd_with_instream(
    stmt: dict[str, Any],
    name: str,
    params: list[dict[str, Any]],
) -> list[str]:
    body = ",".join(_format_param(p) for p in params) if params else "*"
    lines = _emit_card(name, "DD", body)
    instream = stmt["instream"]
    if isinstance(instream, dict):
        data = instream.get("bytes") or ""
        delim = instream.get("retain_delim") or "/*"
    else:
        data = instream or ""
        delim = "/*"
    for line in data.split("\n"):
        if line:
            lines.append(line.rstrip())
    if delim.strip():
        lines.append(delim)
    return lines


_EmitHandler = Callable[[dict[str, Any], str, list[dict[str, Any]]], list[str]]

_EMIT_DISPATCH: dict[str, _EmitHandler] = {
    "//*": _emit_comment,
    "/*": _emit_jes2,
    "IF": _emit_if,
    "ELSE": _emit_else,
    "ENDIF": _emit_endif,
}


def _emit_statement(stmt: dict[str, Any]) -> list[str]:
    """Synthesise a JCL record from kvps when no raw metadata is present."""
    stype = stmt.get("type", "")
    name = (stmt.get("name") or "").strip()
    params = stmt.get("parameters", [])

    handler = _EMIT_DISPATCH.get(stype)
    if handler is not None:
        return handler(stmt, name, params)
    if stype == "DD" and stmt.get("instream") is not None:
        return _emit_dd_with_instream(stmt, name, params)
    body = ",".join(_format_param(p) for p in params)
    return _emit_card(name, stype or "", body)


def convert(parsed: dict[str, Any]) -> str:
    """Render a parsed statement list back to JCL text.

    With record metadata from parse, byte-exact reconstruction.
    Without it (e.g. dict built programmatically), synthesise from kvps.
    """
    out: list[str] = []
    for stmt in parsed.get("statements", []):
        if stmt.get("synthetic"):
            out.extend(stmt.get("instream_records", []))
            continue
        if _has_record_metadata(stmt):
            out.extend(_reconstruct_records(stmt))
        else:
            out.extend(_emit_statement(stmt))
    return "\n".join(out) + "\n"


def _has_record_metadata(stmt: dict[str, Any]) -> bool:
    return bool(stmt.get("record_lens")) or bool(stmt.get("instream_records"))


def _reconstruct_records(stmt: dict[str, Any]) -> list[str]:
    """Rebuild a statement's records byte-for-byte from column metadata."""
    stype = stmt.get("type", "")
    name = stmt.get("name") or ""
    scan_lines = stmt.get("scanned_lines") or []
    record_lens = stmt.get("record_lens") or []
    instream_records = stmt.get("instream_records") or []
    keyword_col = stmt.get("keyword_col") or 0
    cond = stmt.get("conditional")

    out: list[str] = []
    n_records = len(record_lens) if record_lens else (1 if scan_lines or stype else 0)

    for i in range(n_records):
        target_len = record_lens[i] if i < len(record_lens) else 0
        if stype == "//*":
            out.append(_reconstruct_comment(stmt, scan_lines, i, target_len))
        elif stype == "/*":
            out.append(_reconstruct_jes2(stmt, target_len))
        else:
            out.append(
                _reconstruct_default(
                    stmt,
                    stype,
                    name,
                    scan_lines,
                    i,
                    keyword_col,
                    cond,
                    target_len,
                )
            )

    out.extend(instream_records)
    return out


def _reconstruct_comment(
    stmt: dict[str, Any],
    scan_lines: list[dict[str, Any]],
    i: int,
    target_len: int,
) -> str:
    sl = scan_lines[i] if i < len(scan_lines) else {}
    return _pad_to("//*" + (sl.get("comment_text") or ""), target_len)


def _reconstruct_jes2(stmt: dict[str, Any], target_len: int) -> str:
    params = stmt.get("parameters") or []
    body = (params[0].get("key") or "") if params else ""
    return _pad_to("/*" + body, target_len)


def _reconstruct_default(
    stmt: dict[str, Any],
    stype: str,
    name: str,
    scan_lines: list[dict[str, Any]],
    i: int,
    keyword_col: int,
    cond: dict[str, Any] | None,
    target_len: int,
) -> str:
    parts: list[str] = ["//"]
    is_first = i == 0
    if is_first:
        parts.extend(_first_record_prefix(name, stype, keyword_col))
    cur_len = len("".join(parts))
    cur_len = _append_parm_and_comment(parts, scan_lines, i, cur_len)
    cur_len = _append_conditional(parts, stype, is_first, cond, cur_len)
    _append_tail(parts, scan_lines, i, cur_len)
    return _pad_to("".join(parts), target_len)


def _first_record_prefix(name: str, stype: str, keyword_col: int) -> list[str]:
    """JCLCMD is synthetic; emit nothing and let the body land via comment_text."""
    parts = [name]
    cur_len = 2 + len(name)
    keyword = "" if stype == "JCLCMD" else (stype or "")
    if keyword_col > 0:
        target = keyword_col
    elif keyword:
        target = cur_len + 1
    else:
        target = cur_len
    if target > cur_len:
        parts.append(" " * (target - cur_len))
    parts.append(keyword)
    return parts


def _append_parm_and_comment(
    parts: list[str],
    scan_lines: list[dict[str, Any]],
    i: int,
    cur_len: int,
) -> int:
    if i >= len(scan_lines):
        return cur_len
    sl = scan_lines[i]
    parm_text = sl.get("parm_text") or ""
    if parm_text:
        parm_col = sl.get("parm_col") or 0
        if parm_col > cur_len:
            parts.append(" " * (parm_col - cur_len))
        parts.append(parm_text)
        cur_len = len("".join(parts))
    comment_text = sl.get("comment_text") or ""
    if comment_text:
        comment_col = sl.get("comment_col") or 0
        if comment_col > cur_len:
            parts.append(" " * (comment_col - cur_len))
        parts.append(comment_text)
        cur_len = len("".join(parts))
    return cur_len


def _append_conditional(
    parts: list[str],
    stype: str,
    is_first: bool,
    cond: dict[str, Any] | None,
    cur_len: int,
) -> int:
    if not (stype == "IF" and is_first and cond):
        return cur_len
    col = cond.get("col") or 0
    text = cond.get("text") or ""
    comment = cond.get("comment") or ""
    if col > cur_len:
        parts.append(" " * (col - cur_len))
    parts.append(text + " THEN")
    if comment:
        parts.append(" " + comment)
    return len("".join(parts))


def _append_tail(
    parts: list[str],
    scan_lines: list[dict[str, Any]],
    i: int,
    cur_len: int,
) -> None:
    if i >= len(scan_lines):
        return
    tail = scan_lines[i].get("tail") or ""
    if not tail:
        return
    if cur_len < JCL_TXTLEN:
        parts.append(" " * (JCL_TXTLEN - cur_len))
    parts.append(tail)


def _pad_to(line: str, target_len: int) -> str:
    if target_len > len(line):
        return line + " " * (target_len - len(line))
    return line
