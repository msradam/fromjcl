# SPDX-License-Identifier: Apache-2.0
"""Data models for JCL representation."""

import re
from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class Disposition:
    """JCL DISP=(status,normal,abnormal). Defaults to status=SHR."""

    status: str
    normal: str | None = None
    abnormal: str | None = None

    @classmethod
    def parse(cls, value: str | None) -> "Disposition":
        """Parse a DISP= value. Bare or empty returns DISP=SHR."""
        if not value:
            return cls(status="SHR")

        if value.startswith("(") and value.endswith(")"):
            value = value[1:-1]

        parts = [p.strip() for p in value.split(",")]
        return cls(
            status=parts[0] if len(parts) > 0 and parts[0] else "SHR",
            normal=parts[1] if len(parts) > 1 and parts[1] else None,
            abnormal=parts[2] if len(parts) > 2 and parts[2] else None,
        )


@dataclass
class Space:
    """JCL SPACE=(type,(primary,secondary,directory))."""

    type: str
    primary: int
    secondary: int | None = None
    directory: int | None = None

    @classmethod
    def parse(cls, value: str | None) -> "Space | None":
        """Parse a SPACE= value. None on empty or unparseable input."""
        if not value:
            return None

        match = re.match(r"\((\w+),\(?([\d,]+)\)?", value)
        if not match:
            return None

        space_type = match.group(1)
        numbers = [int(n) for n in match.group(2).split(",") if n]

        return cls(
            type=space_type,
            primary=numbers[0] if len(numbers) > 0 else 0,
            secondary=numbers[1] if len(numbers) > 1 else None,
            directory=numbers[2] if len(numbers) > 2 else None,
        )


@dataclass
class DCB:
    """JCL DCB=(RECFM=,LRECL=,BLKSIZE=,DSORG=)."""

    recfm: str | None = None
    lrecl: int | None = None
    blksize: int | None = None
    dsorg: str | None = None

    @classmethod
    def parse(cls, value: str | None) -> "DCB | None":
        """Parse a DCB= value. Returns None for referbacks of the form *.STEP.DD."""
        if not value:
            return None

        # Referback syntax can't be resolved statically
        if value.startswith("*."):
            return None

        if value.startswith("(") and value.endswith(")"):
            value = value[1:-1]

        dcb = cls()
        for part in value.split(","):
            if "=" in part:
                key, val = part.split("=", 1)
                key = key.strip().upper()
                val = val.strip()
                if key == "RECFM":
                    dcb.recfm = val
                elif key == "LRECL":
                    dcb.lrecl = int(val) if val.isdigit() else None
                elif key == "BLKSIZE":
                    dcb.blksize = int(val) if val.isdigit() else None
                elif key == "DSORG":
                    dcb.dsorg = val

        if dcb.recfm or dcb.lrecl or dcb.blksize or dcb.dsorg:
            return dcb
        return None


def _parse_volume(val: str | None) -> list[str] | None:
    """Extract volume serial(s) from a VOLUME= value. REF= referbacks return None."""
    if not val:
        return None
    s = val.strip()
    if s.upper().startswith("REF=") or s.upper().startswith("(REF="):
        return None
    m = re.search(r"SER\s*=\s*(\([^)]*\)|\S+)", s, re.IGNORECASE)
    if not m:
        return None
    inner = m.group(1).rstrip(")").removeprefix("(")
    return [v.strip() for v in inner.split(",") if v.strip()] or None


@dataclass
class Dataset:
    """One dataset on a DD card. The path field is set when the DD uses
    USS/HFS PATH= instead of DSN=; in that case dsn is empty."""

    dsn: str
    disposition: Disposition = field(default_factory=lambda: Disposition("SHR"))
    space: Space | None = None
    dcb: DCB | None = None
    unit: str | None = None
    volumes: list[str] | None = None
    path: str | None = None

    @property
    def dataset_type(self) -> str | None:
        """Infer dataset type from DSORG or directory blocks."""
        if self.dcb and self.dcb.dsorg:
            dsorg_map = {"PS": "SEQ", "PSU": "SEQ", "PO": "PDS", "POU": "PDS"}
            return dsorg_map.get(self.dcb.dsorg.upper())
        if self.space and self.space.directory:
            return "PDS"
        return None

    @classmethod
    def from_parameters(cls, params: list[dict[str, Any]]) -> "Dataset | None":
        """Extract dataset attributes from a DD card's parameter list."""
        dsn = None
        disp = None
        space = None
        dcb = None
        unit = None
        volumes = None
        path = None

        for p in params:
            key = p["key"].upper() if p["key"] else ""
            val = p["value"]

            if key in ("DSN", "DSNAME"):
                dsn = val
            elif key == "PATH":
                path = val.strip("'") if val else val
            elif key == "DISP":
                disp = Disposition.parse(val)
            elif key == "SPACE":
                space = Space.parse(val)
            elif key == "DCB":
                dcb = DCB.parse(val)
            elif key == "UNIT":
                unit = val
            elif key in ("VOL", "VOLUME"):
                volumes = _parse_volume(val)

        if dsn or path:
            return cls(
                dsn=dsn or "",
                disposition=disp or Disposition("SHR"),
                space=space,
                dcb=dcb,
                unit=unit,
                volumes=volumes,
                path=path,
            )
        return None


@dataclass
class DD:
    """One DD card. Concatenated DDs collapse into a single DD with the
    datasets list holding each member in order."""

    name: str
    datasets: list[Dataset] | None = None
    sysout: str | None = None
    dummy: bool = False
    instream: str | None = None

    @classmethod
    def from_statements(cls, stmts: list[dict[str, Any]]) -> "DD":
        """Build DD from one or more statements (handles concatenation)."""
        first = stmts[0]
        name = first["name"].strip() if first.get("name") else ""
        params = first.get("parameters", [])

        sysout = None
        dummy = False
        inst = first.get("instream")
        instream = inst.get("bytes") if isinstance(inst, dict) else inst
        is_instream_dd = instream is not None

        for p in params:
            key = p["key"].upper() if p["key"] else ""
            if key == "SYSOUT":
                sysout = p["value"] or "*"
            elif key == "DUMMY":
                dummy = True
            elif key in ("*", "DATA"):
                is_instream_dd = True

        if sysout:
            return cls(name=name, sysout=sysout)
        if dummy:
            return cls(name=name, dummy=True)
        if is_instream_dd:
            return cls(name=name, instream=instream or "")

        datasets = []
        for stmt in stmts:
            ds = Dataset.from_parameters(stmt.get("parameters", []))
            if ds:
                datasets.append(ds)

        return cls(name=name, datasets=datasets or None)


@dataclass
class Step:
    """One EXEC step. cond holds the COND= operand on EXEC; condition
    holds the inherited IF/THEN/ELSE expression."""

    name: str
    program: str | None = None
    proc: str | None = None
    parm: str | None = None
    region: str | None = None
    cond: str | None = None
    dds: list[DD] = field(default_factory=list)
    condition: str | None = None


@dataclass
class Job:
    """One JOB card plus its steps. JOB-card fields (account, programmer,
    class_, msgclass, msglevel, notify) come from the JOB statement;
    symbols accumulates SET statements visible to all steps."""

    name: str
    account: str | None = None
    programmer: str | None = None
    class_: str | None = None
    msgclass: str | None = None
    msglevel: str | None = None
    notify: str | None = None
    symbols: dict[str, str] = field(default_factory=dict)
    steps: list[Step] = field(default_factory=list)

    @classmethod
    def from_parsed(cls, parsed: dict[str, Any]) -> "Job":
        """Build a Job from parser.parse(...) output."""
        statements = parsed.get("statements", [])

        job = cls(name="UNNAMED")
        current_step: Step | None = None
        # Stack of (condition_text, in_else) frames; supports nested IF and ELSE.
        cond_stack: list[list[Any]] = []

        def effective_condition() -> str | None:
            if not cond_stack:
                return None
            parts: list[str] = []
            for text, in_else in cond_stack:
                if not text:
                    continue
                parts.append(f"NOT ({text})" if in_else else text)
            if not parts:
                return None
            return parts[0] if len(parts) == 1 else " AND ".join(f"({p})" for p in parts)

        # DD concatenation: named DD followed by unnamed continuations.
        dd_group: list[dict[str, Any]] = []

        for stmt in statements:
            stmt_type = stmt.get("type", "")
            stmt_name = (stmt.get("name") or "").strip()
            params = stmt.get("parameters", [])

            if stmt_type == "JOB":
                job.name = stmt_name
                job._parse_job_params(params)

            elif stmt_type == "SET":
                for p in params:
                    if p.get("key") and p.get("value"):
                        job.symbols[p["key"]] = p["value"]

            elif stmt_type == "IF":
                cond = stmt.get("conditional")
                cond_text = cond.get("text") if isinstance(cond, dict) else cond
                cond_stack.append([cond_text, False])

            elif stmt_type == "ELSE":
                if cond_stack:
                    cond_stack[-1][1] = True

            elif stmt_type == "ENDIF":
                if cond_stack:
                    cond_stack.pop()

            elif stmt_type == "EXEC":
                if current_step:
                    if dd_group:
                        current_step.dds.append(DD.from_statements(dd_group))
                        dd_group = []
                    job.steps.append(current_step)

                current_step = Step(name=stmt_name)
                eff = effective_condition()
                if eff:
                    current_step.condition = eff

                for p in params:
                    key = (p.get("key") or "").upper()
                    val = p.get("value")
                    if key == "PGM":
                        current_step.program = val
                    elif key == "PROC":
                        current_step.proc = val
                    elif key == "PARM":
                        current_step.parm = val
                    elif key == "REGION":
                        current_step.region = val
                    elif key == "COND":
                        current_step.cond = val
                    elif val is None and key and not current_step.program and not current_step.proc:
                        # JCL shorthand: bare token on EXEC means PROC=<token>.
                        current_step.proc = key

            elif stmt_type == "DD" and current_step:
                if stmt_name:
                    if dd_group:
                        current_step.dds.append(DD.from_statements(dd_group))
                    dd_group = [stmt]
                else:
                    dd_group.append(stmt)

        if current_step:
            if dd_group:
                current_step.dds.append(DD.from_statements(dd_group))
            job.steps.append(current_step)

        return job

    def _parse_job_params(self, params: list[dict[str, Any]]) -> None:
        for p in params:
            key = p["key"] or ""
            val = p["value"]

            # Positional params: account in parens, programmer in quotes
            if key.startswith("("):
                self.account = key
            elif key.startswith("'"):
                self.programmer = key.strip("'")
            elif key.upper() == "CLASS":
                self.class_ = val
            elif key.upper() == "MSGCLASS":
                self.msgclass = val
            elif key.upper() == "MSGLEVEL":
                self.msglevel = val
            elif key.upper() == "NOTIFY":
                self.notify = val

    def to_dict(self) -> dict[str, Any]:
        """Serialise to a plain dict for JSON / YAML output."""
        return asdict(self)
