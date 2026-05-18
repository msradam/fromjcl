# SPDX-License-Identifier: Apache-2.0
"""Roundtrip: emit JCL text from a parsed statement list."""

from collections.abc import Callable
from typing import Any

JCL_TXTLEN = 71
CONT_COL = 15


def _escape_parm_value(value: str) -> str:
    """Double apostrophes per JCL convention for PARM= strings."""
    return value.replace("'", "''")


def _format_param(kvp: dict[str, Any]) -> str:
    key = kvp.get("key") or ""
    val = kvp.get("value")
    if val is None:
        return key
    # Only the quoted-string PARM shape needs apostrophe escaping.
    # Paren-lists `PARM=(t1,t2,'spaced')` and bare tokens pass through.
    if key.upper() == "PARM" and val:
        if val.startswith("("):
            pass
        elif not (val.startswith("'") and val.endswith("'")):
            val = f"'{_escape_parm_value(val)}'"
        else:
            val = f"'{_escape_parm_value(val[1:-1])}'"
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


def _find_safe_break(seg: str, limit: int) -> int:
    """Find the last safe break point (space, comma, or operator) before limit.
    Can break inside quoted strings at spaces. Returns -1 if no safe break exists."""
    in_quote = False
    last_space = -1
    last_comma = -1
    last_space_in_quote = -1

    for j, c in enumerate(seg[:limit]):
        if c == "'":
            in_quote = not in_quote
        elif c == " ":
            if in_quote:
                last_space_in_quote = j
            else:
                last_space = j
        elif c == "," and not in_quote:
            last_comma = j

    # Prefer comma, then space outside quotes, then space inside quotes
    if last_comma > 0:
        return last_comma
    if last_space > 0:
        return last_space
    return last_space_in_quote


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
            # Special handling for quoted PARM values
            if seg.startswith("PARM='") and seg.endswith("'"):
                lines_from_parm = _emit_quoted_parm(cur, seg, sep)
                lines.extend(lines_from_parm[:-1])  # All but last
                cur = lines_from_parm[-1]  # Last becomes current
                i += 1
            else:
                # Single segment exceeds line; try multiple break strategies
                avail = JCL_TXTLEN - len(cur)

                # Strategy 1: Split at internal comma (depth-1 paren-list)
                split = _last_comma_within(seg, avail)
                if split > 0:
                    lines.append(cur + seg[: split + 1])
                    parts[i] = seg[split + 1 :]
                    cur = cont
                else:
                    # Strategy 2: Find safe break point (space or comma)
                    split = _find_safe_break(seg, avail)
                    if split > 0:
                        lines.append(cur + seg[: split + 1])
                        parts[i] = seg[split + 1 :].lstrip()
                        cur = cont
                        if len(cur + parts[i]) > JCL_TXTLEN:
                            continue
                    else:
                        # Strategy 3: Force break at available space
                        lines.append(cur + seg[:avail])
                        parts[i] = seg[avail:].lstrip()
                        cur = cont
    if cur != cont:
        lines.append(cur)
    return lines


def _emit_quoted_parm(prefix: str, parm_seg: str, sep: str) -> list[str]:
    """Emit a quoted PARM value, breaking long values across records with
    an `X` continuation marker in column 72. The final list element is
    the in-progress line the caller continues building."""
    parm_key = "PARM='"
    parm_value = parm_seg[len(parm_key) : -1]

    lines: list[str] = []
    cont = "//" + " " * (CONT_COL - 2)
    cur = prefix + parm_key
    remaining = parm_value

    while remaining:
        # Leave column 72 free for the X continuation marker.
        avail = JCL_TXTLEN - len(cur)

        if len(remaining) <= avail:
            return lines + [cur + remaining + "'" + sep]

        break_pos = remaining.rfind(" ", 0, avail)
        if break_pos == -1:
            # No space to break on; force a hard break at the limit.
            break_pos = avail

        line = cur + remaining[:break_pos]
        line = line.ljust(JCL_TXTLEN) + "X"
        lines.append(line)

        remaining = remaining[break_pos:].lstrip()
        cur = cont

    # Empty parm value: emit just the closing quote.
    return lines + [cur + "'"]


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
    first_prefix = f"//{name:<8} IF " if name else "//          IF "
    full = f"{first_prefix}{cond_text} THEN"
    if len(full) <= JCL_TXTLEN:
        return [full]
    # Long condition: wrap across continuation records at whitespace.
    cont_prefix = "//          "
    lines: list[str] = []
    remaining = f"{cond_text} THEN"
    cur_prefix = first_prefix
    while True:
        candidate = f"{cur_prefix}{remaining}"
        if len(candidate) <= JCL_TXTLEN:
            lines.append(candidate)
            return lines
        avail = JCL_TXTLEN - len(cur_prefix)
        break_pos = remaining.rfind(" ", 0, avail + 1)
        if break_pos <= 0:
            lines.append(candidate)
            return lines
        lines.append(f"{cur_prefix}{remaining[:break_pos]}")
        remaining = remaining[break_pos + 1 :]
        cur_prefix = cont_prefix


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
    # splitlines() preserves blank lines (they are instream data,
    # not statement terminators).
    for line in data.splitlines():
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
    line = "/*" + body
    # The scanner stores a 70-char body window; trim if the source record was shorter.
    if target_len and target_len < len(line):
        line = line[:target_len]
    return _pad_to(line, target_len)


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
