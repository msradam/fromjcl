# SPDX-License-Identifier: Apache-2.0
"""Pure-Python JCL scanner. Port of `parser/src/scanjcl.c` from Mike
Fulton's JCLParser (https://github.com/MikeFultonDev/JCLParser),
Apache 2.0. Intended to be 1:1 with the C implementation: every field
the C scanner populates is captured and exposed in parse()'s output dict."""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

JCL_RECLEN = 80
JCL_TXTLEN = 71
PREFIX_LEN = 2
STRING_CONTINUE_COLUMN = 15
NAME_LEN = 8
DELIM_LEN = 2
DEFAULT_DELIM = "/*"
EMPTY_DELIM = "  "

NATIONAL = frozenset("@$#")

_EBCDIC_SLASH = 0x61  # EBCDIC '/' shared by cp037/cp500/cp1047
_EBCDIC_CODECS = frozenset({"cp037", "cp500"})
# cp1047 maps JCL characters identically to cp037; remap for portability
# (cp1047 is absent from some Python builds, including CPython 3.14 on macOS).
_EBCDIC_ALIASES: dict[str, str] = {"ebcdic": "cp037", "cp1047": "cp037"}

_KEYWORDS_FULL = [
    "DD",
    "EXEC",
    "SET",
    "IF",
    "ELSE",
    "ENDIF",
    "JOB",
    "PROC",
    "PEND",
    "INCLUDE",
    "JCLLIB",
    "COMMAND",
    "CNTL",
    "ENDCNTL",
    "OUTPUT",
    "XMIT",
    "PRINTDEV",
    "EXPORT",
]
_KEYWORDS_RESTRICTED = [
    "DD",
    "EXEC",
    "SET",
    "IF",
    "ELSE",
    "ENDIF",
    "PROC",
    "PEND",
    "INCLUDE",
    "JCLLIB",
    "COMMAND",
    "ENDCNTL",
    "XMIT",
    "OUTPUT",
    "EXPORT",
]

_JES3_PREFIXES = [
    "*",
    "DATASET",
    "ENDDATASET",
    "ENDPROCESS",
    "FORMAT",
    "MAIN",
    "NET",
    "NETACCT",
    "OPERATOR",
    "PAUSE",
    "PROCESS",
    "ROUTE",
    "SIGNOFF",
    "SIGNON",
]
_JES2_PREFIXES = [
    "$",
    "JOBPARM",
    "MESSAGE",
    "NETACCT",
    "NOTIFY",
    "OUTPUT",
    "PRIORITY",
    "ROUTE",
    "SETUP",
    "SIGNOFF",
    "SIGNON",
    "XEQ",
    "XMIT",
]


class ScanState(Enum):
    # Values mirror the C scanjcl enum (4 intentionally skipped). Do not renumber.
    NotContinued = 0
    ContinueParameter = 1
    ContinueString = 2
    ContinueComment = 3
    ContinueJES3Dataset = 5
    InlineText = 6
    ContinueConditional = 7


class DatasetType(Enum):
    NoDataset = 0
    OutstreamDataset = 1
    InstreamDatasetStar = 2
    InstreamDatasetData = 3


class ParmContext(Enum):
    InKeyword = 1
    InValue = 2
    InQuote = 3
    InParen = 4


@dataclass
class ScannedLine:
    parm_text: str | None = None
    comment_text: str | None = None
    # 0-indexed column positions, used by the emitter to rebuild byte layout.
    parm_col: int = 0
    parm_end_col: int = 0
    comment_col: int = 0
    comment_end_col: int = 0
    # Chars at col 72+ (continuation marker, sequence numbers) preserved verbatim.
    tail: str = ""


@dataclass
class Stmt:
    # Field layout mirrors the C Statement struct in scanjcl.c. Keep order stable.
    type: str
    name: str | None = None
    lines: int = 1
    scan_lines: list[ScannedLine] = field(default_factory=list)
    kvps: list[dict[str, Any]] = field(default_factory=list)
    conditional_text: str | None = None
    conditional_comment: str | None = None
    conditional_col: int = 0
    data_present: bool = False
    data_bytes_buf: str = ""
    data_retain_delim: str = EMPTY_DELIM
    record_lens: list[int] = field(default_factory=list)
    instream_records: list[str] = field(default_factory=list)
    keyword_col: int = 0
    synthetic: bool = False  # scanner-invented stmt (e.g. auto SYSIN DD)

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "type": self.type,
            "name": self.name,
            "lines": self.lines,
            "keyword_col": self.keyword_col,
            "record_lens": self.record_lens.copy(),
            "instream_records": self.instream_records.copy(),
            "parameters": self.kvps.copy(),
            "scanned_lines": [
                {
                    "parm_text": sl.parm_text,
                    "comment_text": sl.comment_text,
                    "parm_col": sl.parm_col,
                    "parm_end_col": sl.parm_end_col,
                    "comment_col": sl.comment_col,
                    "comment_end_col": sl.comment_end_col,
                    "tail": sl.tail,
                }
                for sl in self.scan_lines
            ],
        }
        if self.conditional_text is not None:
            d["conditional"] = {
                "text": self.conditional_text,
                "comment": self.conditional_comment,
                "col": self.conditional_col,
            }
        if self.data_present:
            bytes_val = self.data_bytes_buf or None
            d["instream"] = {
                "bytes": bytes_val,
                "retain_delim": self.data_retain_delim,
            }
        return d


def _skip_blanks(text: str, start: int, end: int) -> tuple[int, int]:
    """Mirror C skipBlanks: trim leading and trailing blanks in [start, end)."""
    while start < end and text[start] == " ":
        start += 1
    if start < end:
        e = end - 1
        while e > start and text[e] == " ":
            e -= 1
        end = e + 1
    return start, end


def _is_name_char(c: str) -> bool:
    return (c.isascii() and c.isalpha()) or c.isdigit() or c in NATIONAL


def _is_valid_name(buf: str) -> tuple[bool, int]:
    """buf is text AFTER the // prefix. Return (is_valid, name_len)."""
    if not buf:
        return False, 0
    c0 = buf[0]
    if not ((c0.isascii() and c0.isalpha()) or c0 in NATIONAL):
        return False, 0

    dot = 0
    i = 1
    limit = NAME_LEN * 2 + 1
    while i < limit and i < len(buf):
        c = buf[i]
        if c == " ":
            return True, i
        if not _is_name_char(c):
            if c == "." and dot == 0:
                dot = i
                if i > NAME_LEN:
                    return False, i
            else:
                return False, i
        i += 1
    if i - dot > NAME_LEN:
        return False, i
    ok = len(buf) > NAME_LEN and buf[NAME_LEN] == " "
    return ok, i


def _word_eq(buf: str, word: str) -> bool:
    return buf.startswith(word) and len(buf) > len(word) and buf[len(word)] == " "


def _word_starts(buf: str, word: str) -> bool:
    return buf.startswith(word)


def _resolve_encoding(raw: bytes, encoding: str) -> str:
    """Resolve 'auto' and known aliases to a concrete codec name."""
    if encoding == "auto":
        return (
            "cp037"
            if (len(raw) >= 2 and raw[0] == _EBCDIC_SLASH and raw[1] == _EBCDIC_SLASH)
            else "latin-1"
        )
    return _EBCDIC_ALIASES.get(encoding, encoding)


def _records_from_bytes(raw: bytes, encoding: str = "auto") -> Iterator[tuple[str, str]]:
    """Yield (original, padded) per record. CRLF and EBCDIC NL are normalised."""
    resolved = _resolve_encoding(raw, encoding)
    if resolved in _EBCDIC_CODECS:
        decoded = raw.decode(resolved, errors="replace").replace("\x85", "\n")
        if "\n" in decoded:
            lines_text = decoded.split("\n")
            if lines_text and lines_text[-1] == "":
                lines_text.pop()
        else:
            lines_text = [decoded[i : i + JCL_RECLEN] for i in range(0, len(decoded), JCL_RECLEN)]
        for text in lines_text:
            if len(text) > JCL_RECLEN:
                text = text[:JCL_RECLEN]
            padded = text.ljust(JCL_RECLEN, " ")
            yield text, padded
    else:
        raw = raw.replace(b"\r\n", b"\n").replace(b"\r", b"\n")
        # \x1a is the DOS EOF sentinel. Truncate so it does not land in synthetic SYSIN.
        eof = raw.find(b"\x1a")
        if eof != -1:
            raw = raw[:eof]
        lines = raw.split(b"\n")
        if lines and lines[-1] == b"":
            lines.pop()
        for line in lines:
            text = line.decode(resolved, errors="replace")
            if len(text) > JCL_RECLEN:
                text = text[:JCL_RECLEN]
            padded = text.ljust(JCL_RECLEN, " ")
            yield text, padded


class Scanner:
    def __init__(self) -> None:
        self.stmts: list[Stmt] = []
        self.state = ScanState.NotContinued
        self.dataset_type = DatasetType.NoDataset
        self.delimiter = EMPTY_DELIM
        self._current_raw: str = ""

    @property
    def _cur(self) -> Stmt:
        return self.stmts[-1]

    def _add_stmt(self, stmt_type: str, name: str | None) -> None:
        self.stmts.append(Stmt(type=stmt_type, name=name))

    def _add_to_stmt(self) -> None:
        self._cur.lines += 1

    def _add_scanned_line(
        self,
        parm_text: str | None,
        comment_text: str | None,
        parm_col: int = 0,
        parm_end_col: int = 0,
        comment_col: int = 0,
        comment_end_col: int = 0,
    ) -> None:
        tail = self._current_raw[JCL_TXTLEN:] if len(self._current_raw) > JCL_TXTLEN else ""
        self._cur.scan_lines.append(
            ScannedLine(
                parm_text=parm_text,
                comment_text=comment_text,
                parm_col=parm_col,
                parm_end_col=parm_end_col,
                comment_col=comment_col,
                comment_end_col=comment_end_col,
                tail=tail,
            )
        )

    def _append_scanned_comment(self, text: str, start: int, end: int) -> None:
        """C appendScannedComment."""
        start, end = _skip_blanks(text, start, end)
        chunk = text[start:end]
        tail = self._cur.scan_lines[-1]
        existing = tail.comment_text or ""
        tail.comment_text = existing + chunk

    def _add_kvp(
        self,
        key: str,
        value: str | None,
        comment: str | None,
        has_newline: bool,
    ) -> None:
        self._cur.kvps.append(
            {
                "key": key,
                "value": value,
                "comment": comment,
                "has_newline": has_newline,
            }
        )

    def _get_subparm(self, name: str) -> str | None:
        for kvp in self._cur.kvps:
            if kvp["key"] == name:
                value: str | None = kvp["value"]
                return value
        return None

    def _scan_parameters(self, text: str, column: int) -> None:
        in_string = self.state == ScanState.ContinueString
        in_comment = self.state == ScanState.ContinueComment
        in_parameter = False

        start = column
        end = JCL_TXTLEN
        comment_start = 0
        comment_end = 0

        if not in_comment:
            i = column
            while i < JCL_TXTLEN and text[i] == " ":
                i += 1
            start = i
            while i < JCL_TXTLEN:
                c = text[i]
                if c == "'":
                    in_string = not in_string
                elif not in_string and c == " ":
                    if i > 0 and text[i - 1] == ",":
                        in_parameter = True
                    end = i
                    comment_start = i
                    comment_end = JCL_TXTLEN
                    break
                i += 1
            # Column-70 special case: trailing comma with no blank required.
            if not in_string and comment_start == 0 and text[JCL_TXTLEN - 1] == ",":
                in_parameter = True

            comment_start, comment_end = _skip_blanks(text, comment_start, comment_end)
            parm_text = text[start:end] if end > start else None
            comment_text = text[comment_start:comment_end] if comment_end > comment_start else None
            self._add_scanned_line(
                parm_text,
                comment_text,
                parm_col=start,
                parm_end_col=max(start, end),
                comment_col=comment_start,
                comment_end_col=comment_end,
            )

        if in_string:
            self.state = ScanState.ContinueString
        elif in_parameter:
            self.state = ScanState.ContinueParameter
        elif text[JCL_TXTLEN] != " ":
            self.state = ScanState.ContinueComment
        else:
            self.state = ScanState.NotContinued
            self._scan_sub_parameters()

            if self.dataset_type in (
                DatasetType.InstreamDatasetStar,
                DatasetType.InstreamDatasetData,
            ):
                dlm_orig = self._get_subparm("DLM")
                if (
                    dlm_orig is not None
                    and len(dlm_orig) == DELIM_LEN + 2
                    and dlm_orig[0] == dlm_orig[-1] == "'"
                ):
                    dlm = dlm_orig[1:3]
                else:
                    dlm = DEFAULT_DELIM
                self.state = ScanState.InlineText
                self.delimiter = dlm

    def _scan_sub_parameters(self) -> None:
        lines = self._cur.scan_lines
        if not lines:
            return

        context = ParmContext.InKeyword
        prev_context = context
        paren_nest = 0

        text = lines[0].parm_text or ""
        start = 0
        end = len(text)
        cur_parm = 0
        cur_value = -1
        line_idx = 0
        cur_line_comment = lines[0].comment_text

        while line_idx < len(lines):
            i = start
            while i < end:
                c = text[i]
                if context == ParmContext.InKeyword:
                    if c == "(":
                        paren_nest += 1
                    elif c == ")" and paren_nest > 0:
                        paren_nest -= 1
                    elif c == "=" and paren_nest == 0:
                        context = ParmContext.InValue
                        cur_value = i + 1
                    elif c == "," and paren_nest == 0:
                        if i + 1 == end:
                            comment = cur_line_comment
                            hn = True
                        else:
                            comment = None
                            hn = False
                        self._add_kvp(text[cur_parm:i], None, comment, hn)
                        cur_parm = i + 1
                elif context == ParmContext.InValue:
                    if c == "," and paren_nest == 0:
                        context = ParmContext.InKeyword
                        key = text[cur_parm : cur_value - 1]
                        value = text[cur_value:i]
                        if i + 1 == end:
                            comment = cur_line_comment
                            hn = True
                        else:
                            comment = None
                            hn = False
                        self._add_kvp(key, value, comment, hn)
                        cur_parm = i + 1
                    elif c == "'":
                        context = ParmContext.InQuote
                        prev_context = ParmContext.InValue
                    elif c == "(":
                        paren_nest += 1
                        context = ParmContext.InParen
                elif context == ParmContext.InQuote:
                    if c == "'":
                        context = prev_context
                elif context == ParmContext.InParen:
                    if c == "'":
                        context = ParmContext.InQuote
                        prev_context = ParmContext.InParen
                    elif c == ")":
                        paren_nest -= 1
                        if paren_nest == 0:
                            context = ParmContext.InValue
                i += 1

            trailing_comment = cur_line_comment

            next_idx = line_idx + 1
            has_next = next_idx < len(lines)
            next_text = (lines[next_idx].parm_text or "") if has_next else None
            next_comment = lines[next_idx].comment_text if has_next else None

            mid_group = context in (ParmContext.InQuote, ParmContext.InParen) or paren_nest > 0
            if has_next and mid_group:
                frag = text[cur_parm:end]
                new_start = len(frag)
                text = frag + (next_text or "")
                end = len(text)
                if cur_value >= 0:
                    cur_value -= cur_parm
                cur_parm = 0
                start = new_start
                line_idx = next_idx
                cur_line_comment = next_comment
            else:
                if cur_parm < end:
                    if context == ParmContext.InKeyword:
                        self._add_kvp(text[cur_parm:end], None, trailing_comment, True)
                    else:
                        key = text[cur_parm : cur_value - 1]
                        value = text[cur_value:end]
                        self._add_kvp(key, value, trailing_comment, True)
                if has_next:
                    text = next_text or ""
                    start = 0
                    end = len(text)
                    cur_parm = 0
                    line_idx = next_idx
                    cur_line_comment = next_comment
                else:
                    break

    def _scan_simple(
        self,
        text: str,
        stmt_type: str,
        name: str | None,
        column: int,
        with_params: bool,
    ) -> None:
        self._add_stmt(stmt_type, name)
        if with_params:
            self._scan_parameters(text, column)
        elif stmt_type == "JCLCMD":
            # Capture the unrecognised body verbatim so the emitter can replay it.
            s, e = _skip_blanks(text, column, JCL_TXTLEN)
            body = text[s:e] if e > s else ""
            self._add_scanned_line(
                None,
                body,
                comment_col=s,
                comment_end_col=s + len(body),
            )

    def _scan_dd(self, text: str, name: str | None, column: int) -> None:
        self._add_stmt("DD", name)
        i = column
        while i < len(text) and text[i] == " ":
            i += 1
        rest = text[i:]
        dst = DatasetType.OutstreamDataset
        if rest[:1] == "*" and rest[1:2] in (" ", ","):
            dst = DatasetType.InstreamDatasetStar
        elif rest.startswith("DATA") and rest[4:5] in (" ", ","):
            dst = DatasetType.InstreamDatasetData
        self.dataset_type = dst
        self._scan_parameters(text, column)

    def _scan_if(self, text: str, name: str | None, column: int) -> None:
        self._add_stmt("IF", name)
        self._scan_conditional(text, column)

    def _scan_conditional(self, text: str, column: int) -> None:
        i = column
        complete = False
        then_keylen = 4
        while i < JCL_TXTLEN:
            if (
                i > 0
                and text[i - 1] == " "
                and i < JCL_TXTLEN - then_keylen
                and text[i : i + then_keylen] == "THEN"
                and text[i + then_keylen] == " "
            ):
                complete = True
                i -= 1
                break
            i += 1
        s, e = _skip_blanks(text, column, i)
        frag = text[s:e]
        existing = self._cur.conditional_text or ""
        if not existing:
            # Only the first IF record carries a meaningful conditional_col.
            self._cur.conditional_col = s
            self._cur.conditional_text = frag
        else:
            # Continuation indent acts as a token separator: `OR\n  COND` -> `OR COND`.
            self._cur.conditional_text = existing + " " + frag

        if complete:
            i += then_keylen
            self.state = ScanState.NotContinued
            start = i + 1
            end = start + len(text[start:].rstrip("\x00"))  # text is padded
            s2, e2 = _skip_blanks(text, start, end)
            if e2 > s2:
                self._cur.conditional_comment = text[s2:e2]
        else:
            self.state = ScanState.ContinueConditional

    def _scan_comment_stmt(self, text: str) -> None:
        """Comment text is cropped to the original line length."""
        self._add_stmt("//*", None)
        raw_len = len(self._current_raw)
        content_end = max(PREFIX_LEN + 1, min(raw_len, JCL_RECLEN))
        comment_text = self._current_raw[PREFIX_LEN + 1 : content_end]
        self._add_scanned_line(
            None,
            comment_text,
            comment_col=PREFIX_LEN + 1,
            comment_end_col=PREFIX_LEN + 1 + len(comment_text),
        )

    def _scan_jes2_control(self, text: str) -> None:
        self._add_stmt("/*", None)
        body_len = JCL_TXTLEN - PREFIX_LEN + 1
        key = text[PREFIX_LEN : PREFIX_LEN + body_len]
        self._add_kvp(key, None, None, True)
        # Minimal scan line so _reconstruct_jes2 can recover cols 73-80 via tail.
        self._add_scanned_line(None, None)

    def _scan_jes3_control(self, text: str, column: int) -> None:
        self._add_stmt("//*", None)
        body = text[column:]
        if _word_starts(body, "DATASET"):
            self.state = ScanState.ContinueJES3Dataset
        else:
            raw_len = len(self._current_raw)
            content_end = max(column, min(raw_len, JCL_RECLEN))
            comment_text = self._current_raw[column:content_end] or None
            self._add_scanned_line(
                None,
                comment_text,
                comment_col=column,
                comment_end_col=column + len(comment_text or ""),
            )

    def _dispatch(
        self,
        text: str,
        column: int,
        keywords: list[str],
        allow_unknown_command: bool,
    ) -> None:
        i = column
        while i < JCL_TXTLEN and text[i] == " ":
            i += 1
        rest = text[i:]

        for kw in keywords:
            if _word_eq(rest, kw):
                after = i + len(kw) + 1
                while after < JCL_TXTLEN and text[after] == " ":
                    after += 1
                name = text[PREFIX_LEN:column] or None
                kw_col = i  # column where the keyword starts
                if kw == "DD":
                    self._scan_dd(text, name, after)
                elif kw == "IF":
                    self._scan_if(text, name, after)
                else:
                    with_params = kw in (
                        "EXEC",
                        "JOB",
                        "SET",
                        "PROC",
                        "JCLLIB",
                        "INCLUDE",
                        "COMMAND",
                        "OUTPUT",
                        "XMIT",
                        "EXPORT",
                    )
                    self._scan_simple(text, kw, name, after, with_params)
                if self.stmts:
                    self._cur.keyword_col = kw_col
                return

        if allow_unknown_command:
            # //<blank> form with an unrecognized keyword: either JCLCMD or
            # the null statement (all-blank record).
            if self._blank_after_prefix(text):
                self._scan_simple(text, "", None, column, False)
            else:
                self._scan_simple(text, "JCLCMD", None, column, False)
        else:
            raise ValueError(f"Invalid JCL record: unknown statement type near '{rest[:16]}'")

    def _blank_after_prefix(self, text: str) -> bool:
        """True if everything after the // or /* prefix is blank up to col 72."""
        return all(c == " " for c in text[PREFIX_LEN:JCL_TXTLEN])

    def _process_jcl_record(self, text: str) -> None:
        if text[0] == "/":
            if text[1] == "/":
                if text[2] == "*":
                    if self._is_jes3_control(text, PREFIX_LEN + 1):
                        self._scan_jes3_control(text, PREFIX_LEN + 1)
                    else:
                        self._scan_comment_stmt(text)
                else:
                    ok, name_len = _is_valid_name(text[2:])
                    if ok:
                        self._dispatch(text, PREFIX_LEN + name_len, _KEYWORDS_FULL, False)
                    elif text[2] == " ":
                        self._dispatch(text, PREFIX_LEN + 1, _KEYWORDS_RESTRICTED, True)
                    else:
                        raise ValueError(f"Invalid JCL record: '//{text[2]}' prefix")
            elif text[1] == "*":
                if self._is_jes2_control(text, PREFIX_LEN):
                    self._scan_jes2_control(text)
                elif self._blank_after_prefix(text):
                    # Bare `/*` separator. Capture as its own statement
                    # so it does not bleed into the previous one.
                    self._scan_jes2_control(text)
            else:
                self._generate_sysin(text)
        else:
            self._generate_sysin(text)

    def _is_jes3_control(self, text: str, column: int) -> bool:
        body = text[column:]
        if body.startswith("*") and len(body) > 1 and body[1] == "*":
            return False
        return any(_word_starts(body, kw) for kw in _JES3_PREFIXES)

    def _is_jes2_control(self, text: str, column: int) -> bool:
        body = text[column:]
        return any(_word_starts(body, kw) for kw in _JES2_PREFIXES)

    def _generate_sysin(self, text: str) -> None:
        """Synthetic //SYSIN DD * for data with no DD card."""
        self._add_stmt("DD", "SYSIN ")
        self._cur.synthetic = True
        self._add_scanned_line("*", None)
        self._scan_sub_parameters()
        self.dataset_type = DatasetType.InstreamDatasetStar
        self.state = ScanState.InlineText
        self.delimiter = DEFAULT_DELIM
        self._process_inline_record(text)

    def _process_inline_record(self, text: str) -> None:
        dlm = self.delimiter
        dst = self.dataset_type
        retain: str | None = None

        if dst in (
            DatasetType.InstreamDatasetData,
            DatasetType.InstreamDatasetStar,
        ) and text.startswith(dlm):
            self.dataset_type = DatasetType.NoDataset
            self.state = ScanState.NotContinued
            retain = dlm
        if dst != DatasetType.InstreamDatasetData:  # noqa: SIM102, has elif
            if text.startswith(DEFAULT_DELIM):
                self.state = ScanState.NotContinued
                self.dataset_type = DatasetType.NoDataset
                retain = DEFAULT_DELIM
            elif text.startswith("//"):
                self.state = ScanState.NotContinued
                self.dataset_type = DatasetType.NoDataset
                retain = EMPTY_DELIM

        # Mirror C addToInlineData: allocate data struct on first call;
        # either append 72 chars + \n, or set retainDelim.
        stmt = self._cur
        if not stmt.data_present:
            stmt.data_present = True
            stmt.data_retain_delim = EMPTY_DELIM

        if retain is not None:
            stmt.data_retain_delim = retain
        else:
            stmt.data_bytes_buf += text[: JCL_TXTLEN + 1] + "\n"

        if retain is not None and retain == EMPTY_DELIM:
            self._process_jcl_record(text)

    def _process_continued_comment(self, text: str) -> None:
        if text[0] != "/" or text[1] != "/" or text[2] != " ":
            # A new JCL statement arrived while continuation was expected
            # (e.g. a parameter line whose content reached col 72 set the
            # flag spuriously). Treat this record as the start of a fresh
            # statement rather than a hard error.
            self.state = ScanState.NotContinued
            self._process_jcl_record(text)
            return
        self._add_to_stmt()
        self._scan_parameters(text, PREFIX_LEN + 1)

    def _process_continued_string(self, text: str) -> None:
        if text[0] != "/" or text[1] != "/":
            raise ValueError("Invalid continued string record: missing //")
        for col in range(PREFIX_LEN, STRING_CONTINUE_COLUMN):
            if text[col] != " ":
                raise ValueError(
                    f"Continued string must have blanks through col {STRING_CONTINUE_COLUMN}"
                )
        self._add_to_stmt()
        self._scan_parameters(text, PREFIX_LEN)

    def _process_continued_conditional(self, text: str) -> None:
        if text[0] != "/" or text[1] != "/" or text[2] != " ":
            raise ValueError("Invalid continued conditional record")
        self._add_to_stmt()
        self._scan_conditional(text, PREFIX_LEN)

    def _process_continued_parameter(self, text: str) -> None:
        # //* inside continued params: append to the current scan line's
        # comment_text with a leading newline. No addToStatement.
        if text[0] == text[1] == "/" and text[2] == "*":
            tail = self._cur.scan_lines[-1]
            existing = tail.comment_text or ""
            tail.comment_text = existing + "\n"
            self._append_scanned_comment(text, PREFIX_LEN + 1, JCL_TXTLEN)
            return
        if text[0] != "/" or text[1] != "/" or text[2] != " ":
            # Same lenient recovery as _process_continued_comment.
            self.state = ScanState.NotContinued
            self._process_jcl_record(text)
            return
        self._add_to_stmt()
        self._scan_parameters(text, PREFIX_LEN + 1)

    def _process_jes3_continued_dataset(self, text: str) -> None:
        if text[0] == text[1] == "/" and text[2] == "*" and _word_starts(text[3:], "ENDDATASET"):
            # C: addStatement(0, JES3_KEYWORD); opens a new //* stmt.
            self._add_stmt("//*", None)
            self.state = ScanState.NotContinued
        else:
            self._add_to_stmt()

    def process_record(self, text: str, raw: str | None = None) -> None:
        self._current_raw = raw if raw is not None else text.rstrip()
        was_inline = self.state == ScanState.InlineText
        current = self.state
        before = len(self.stmts)
        if current == ScanState.NotContinued:
            self._process_jcl_record(text)
        elif current == ScanState.InlineText:
            self._process_inline_record(text)
        elif current == ScanState.ContinueComment:
            self._process_continued_comment(text)
        elif current == ScanState.ContinueString:
            self._process_continued_string(text)
        elif current == ScanState.ContinueParameter:
            self._process_continued_parameter(text)
        elif current == ScanState.ContinueConditional:
            self._process_continued_conditional(text)
        elif current == ScanState.ContinueJES3Dataset:
            self._process_jes3_continued_dataset(text)
        else:
            raise RuntimeError(f"Unreachable scan state: {current}")

        if len(self.stmts) > before:
            self._cur.record_lens.append(len(self._current_raw))
        elif self.stmts and was_inline:
            self._cur.instream_records.append(self._current_raw)
        elif self.stmts:
            self._cur.record_lens.append(len(self._current_raw))


def parse_bytes(data: bytes, encoding: str = "auto") -> dict[str, Any]:
    """Parse JCL from a bytes buffer."""
    scanner = Scanner()
    for original, padded in _records_from_bytes(data, encoding):
        scanner.process_record(padded, raw=original)
    return {"statements": [s.to_dict() for s in scanner.stmts]}


def parse(path: str, encoding: str = "auto") -> dict[str, Any]:
    """Parse JCL from a file path."""
    return parse_bytes(Path(path).read_bytes(), encoding)
