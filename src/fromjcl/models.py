"""Data models for JCL representation."""

from dataclasses import dataclass, field, asdict
from typing import Any
import re


@dataclass
class Disposition:
    """Dataset disposition (DISP parameter)."""

    status: str
    normal: str | None = None
    abnormal: str | None = None

    @classmethod
    def parse(cls, value: str | None) -> "Disposition":
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
    """Dataset space allocation (SPACE parameter)."""

    type: str
    primary: int
    secondary: int | None = None
    directory: int | None = None

    @classmethod
    def parse(cls, value: str | None) -> "Space | None":
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
    """Dataset control block attributes (DCB parameter)."""

    recfm: str | None = None
    lrecl: int | None = None
    blksize: int | None = None
    dsorg: str | None = None

    @classmethod
    def parse(cls, value: str | None) -> "DCB | None":
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


@dataclass
class Dataset:
    """A single dataset reference."""

    dsn: str
    disposition: Disposition = field(default_factory=lambda: Disposition("SHR"))
    space: Space | None = None
    dcb: DCB | None = None
    unit: str | None = None
    volumes: list[str] | None = None

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
    def from_parameters(cls, params: list[dict]) -> "Dataset | None":
        dsn = None
        disp = None
        space = None
        dcb = None
        unit = None
        volumes = None

        for p in params:
            key = p["key"].upper() if p["key"] else ""
            val = p["value"]

            if key in ("DSN", "DSNAME"):
                dsn = val
            elif key == "DISP":
                disp = Disposition.parse(val)
            elif key == "SPACE":
                space = Space.parse(val)
            elif key == "DCB":
                dcb = DCB.parse(val)
            elif key == "UNIT":
                unit = val
            elif key in ("VOL", "VOLUME"):
                if val and "=" in val:
                    _, volval = val.split("=", 1)
                    if volval.startswith("("):
                        volumes = [v.strip() for v in volval[1:-1].split(",")]
                    else:
                        volumes = [volval]
                elif val:
                    volumes = [val]

        if dsn:
            return cls(
                dsn=dsn,
                disposition=disp or Disposition("SHR"),
                space=space,
                dcb=dcb,
                unit=unit,
                volumes=volumes,
            )
        return None


@dataclass
class DD:
    """A DD statement."""

    name: str
    datasets: list[Dataset] | None = None
    sysout: str | None = None
    dummy: bool = False
    instream: str | None = None

    @classmethod
    def from_statements(cls, stmts: list[dict]) -> "DD":
        """Build DD from one or more statements (handles concatenation)."""
        first = stmts[0]
        name = first["name"].strip() if first.get("name") else ""
        params = first.get("parameters", [])

        sysout = None
        dummy = False
        instream = first.get("instream")
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

        return cls(name=name, datasets=datasets if datasets else None)


@dataclass
class Step:
    """An EXEC statement and its DDs."""

    name: str
    program: str | None = None
    proc: str | None = None
    parm: str | None = None
    region: str | None = None
    cond: str | None = None
    dds: list[DD] = field(default_factory=list)
    condition: str | None = None  # From IF/THEN/ELSE


@dataclass
class Job:
    """A JCL job."""

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
    def from_parsed(cls, parsed: dict) -> "Job":
        statements = parsed.get("statements", [])

        job = cls(name="UNNAMED")
        current_step: Step | None = None
        pending_dds: list[dict] = []
        current_condition: str | None = None

        for stmt in statements:
            stmt_type = stmt.get("type", "")
            stmt_name = stmt.get("name", "")
            stmt_name = stmt_name.strip() if stmt_name else ""
            params = stmt.get("parameters", [])

            if stmt_type == "JOB":
                job.name = stmt_name
                job._parse_job_params(params)

            elif stmt_type == "SET":
                for p in params:
                    if p.get("key") and p.get("value"):
                        job.symbols[p["key"]] = p["value"]

            elif stmt_type == "IF":
                current_condition = stmt.get("conditional")

            elif stmt_type == "ENDIF":
                current_condition = None

            elif stmt_type == "EXEC":
                if current_step:
                    _flush_pending_dds(current_step, pending_dds)
                    job.steps.append(current_step)
                    pending_dds = []

                current_step = Step(name=stmt_name)
                if current_condition:
                    current_step.condition = current_condition

                for p in params:
                    key = p["key"].upper() if p["key"] else ""
                    val = p["value"]
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
                    elif (
                        val is None
                        and key
                        and not current_step.program
                        and not current_step.proc
                    ):
                        # Implicit proc call: EXEC MYPROC
                        current_step.proc = key

            elif stmt_type == "DD" and current_step:
                if stmt_name:
                    _flush_pending_dds(current_step, pending_dds)
                    pending_dds = [stmt]
                else:
                    # Concatenation: DD without name continues previous
                    pending_dds.append(stmt)

        if current_step:
            _flush_pending_dds(current_step, pending_dds)
            job.steps.append(current_step)

        return job

    def _parse_job_params(self, params: list[dict]) -> None:
        for p in params:
            key = p["key"] if p["key"] else ""
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
        return asdict(self)


def _flush_pending_dds(step: Step, pending: list[dict]) -> None:
    if pending:
        step.dds.append(DD.from_statements(pending))
