# SPDX-License-Identifier: Apache-2.0
"""Classify JCL steps into target-neutral intent objects.

Every renderer (zoau, ansible/zos_core, zosmf, makefile) consumes the
same intent dataclasses, so utility-program parsing (IDCAMS SYSIN,
IEBGENER PATH semantics, ADRDSSU control statements, etc.) lives here
once instead of once per target. classify_step(step) returns the
intent; renderers dispatch by isinstance.

A Fallback result means the classifier could not extract a clean
intent and the renderer should produce a low-fidelity passthrough
(mvscmd, zos_mvs_raw, or a comment) plus the reason.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from fromjcl.converters.common import (
    build_dd_map,
    get_dd_instream,
    get_dd_name,
    get_sysin,
    strip_parm_quotes,
    sysin_is_dummy,
)
from fromjcl.models import Dataset, Step


@dataclass
class DatasetOps:
    """IEFBR14 dataset allocation and deletion (no program logic)."""

    creates: list[tuple[str, Dataset]]  # (dd_name, dataset)
    deletes: list[str]  # dsns


@dataclass
class CopyDataset:
    """IEBGENER, IEBCOPY, or IEBGENER-equivalent copy operation."""

    src_dsn: str | None = None
    dest_dsn: str | None = None
    src_dataset: Dataset | None = None
    dest_dataset: Dataset | None = None
    instream: str | None = None
    to_sysout: bool = False
    src_path: str | None = None  # USS/HFS source (PATH= on the source DD)


@dataclass
class DeleteDatasets:
    """IDCAMS DELETE of one or more datasets."""

    dsns: list[str]


@dataclass
class TSOCommands:
    """IKJEFT01 SYSTSIN block: a sequence of TSO commands."""

    commands: list[str]


@dataclass
class ShellCommand:
    """BPXBATCH SH passthrough. Low-fidelity; the inner shell is opaque."""

    cmd: str
    env_lines: list[str] = field(default_factory=list)
    stdin_path: str | None = None
    stdout_path: str | None = None
    stderr_path: str | None = None


@dataclass
class PathRead:
    """Read a USS file's contents (IEBGENER PATH=...,SYSUT2=SYSOUT)."""

    path: str


@dataclass
class BackupRestore:
    """ADRDSSU DUMP or RESTORE."""

    operation: str  # "dump" or "restore"
    patterns: list[str]
    target_dsn: str | None = None
    replace: bool = False


@dataclass
class IEHListOps:
    """IEHLIST LISTPDS and LISTVTOC operations."""

    pds_dsns: list[str]
    vtoc_volumes: list[str]


@dataclass
class IEHPROGMOps:
    """IEHPROGM RENAME and SCRATCH operations."""

    renames: list[tuple[str, str, str | None]]  # (dsn, newname, member)
    scratches: list[tuple[str, str | None]]  # (dsn, member)


@dataclass
class DefineGDG:
    """IDCAMS DEFINE GENERATIONDATAGROUP."""

    name: str
    limit: int | None = None


@dataclass
class AlterRename:
    """IDCAMS ALTER ... NEWNAME(...)."""

    old_dsn: str
    new_dsn: str


@dataclass
class TextReplace:
    """SORT FINDREP=(IN=,OUT=) text substitution."""

    dsn: str
    find: str
    replace: str


@dataclass
class TextSearch:
    """ISRSUPC SRCHFOR pattern search."""

    dsn: str
    pattern: str


@dataclass
class ListCatalog:
    """IDCAMS LISTCAT. The entries field handles the ENTRIES form, level handles LVL."""

    entries: list[str] = field(default_factory=list)
    level: str | None = None


@dataclass
class Fallback:
    """Classifier could not extract a clean intent. The renderer emits a
    low-fidelity passthrough plus the reason as a comment."""

    reason: str


StepIntent = (
    DatasetOps
    | CopyDataset
    | DeleteDatasets
    | DefineGDG
    | AlterRename
    | TextReplace
    | TextSearch
    | ListCatalog
    | TSOCommands
    | ShellCommand
    | PathRead
    | BackupRestore
    | IEHListOps
    | IEHPROGMOps
    | Fallback
)


def classify_step(step: Step) -> StepIntent:
    """Return the intent for the step. PROCs and unknown programs return Fallback."""
    if step.proc:
        return Fallback(reason=f"PROC {step.proc} requires manual expansion")

    if not step.program:
        return Fallback(reason="No program specified")

    pgm = step.program.upper()

    if pgm == "IEFBR14":
        return _classify_iefbr14(step)
    if pgm in ("IEBGENER", "ICEGENER"):
        return _classify_iebgener(step)
    if pgm == "IEBCOPY":
        return _classify_iebcopy(step)
    if pgm == "IDCAMS":
        return _classify_idcams(step)
    if pgm in ("SORT", "ICEMAN"):
        return _classify_sort(step)
    if pgm == "ISRSUPC":
        return _classify_isrsupc(step)
    if pgm in ("IKJEFT01", "IKJEFT1A", "IKJEFT1B"):
        return _classify_tso(step)
    if pgm == "ADRDSSU":
        return _classify_adrdssu(step)
    if pgm in ("BPXBATCH", "BPXBATSL"):
        return _classify_bpxbatch(step)
    if pgm == "IEHLIST":
        return _classify_iehlist(step)
    if pgm == "IEHPROGM":
        return _classify_iehprogm(step)

    return Fallback(reason=f"No opinionated mapping for {pgm}")


def _classify_iefbr14(step: Step) -> DatasetOps:
    creates: list[tuple[str, Dataset]] = []
    deletes: list[str] = []

    for dd in step.dds:
        name = get_dd_name(dd)
        if name.upper() in ("STEPLIB", "JOBLIB"):
            continue
        if dd.dummy or dd.sysout or dd.instream is not None or not dd.datasets:
            continue

        for ds in dd.datasets:
            disp = ds.disposition
            # JCL DISP semantics for IEFBR14 (the no-op program used
            # as an allocate/delete trick): NEW+CATLG/KEEP creates the
            # dataset on success; OLD/MOD/SHR with normal-or-abnormal
            # DELETE deletes it. We translate only these two shapes.
            if disp.status == "NEW" and disp.normal in ("CATLG", "KEEP"):
                creates.append((name, ds))
            elif (disp.normal == "DELETE" or disp.abnormal == "DELETE") and disp.status in (
                "OLD",
                "MOD",
                "SHR",
            ):
                deletes.append(ds.dsn)

    return DatasetOps(creates=creates, deletes=deletes)


@dataclass
class _IEBGenerInfo:
    """Inputs distilled from a step's DDs for IEBGENER classification."""

    sysut1_dsn: str | None = None
    sysut1_path: str | None = None
    sysut1_instream: str | None = None
    sysut1_dataset: Dataset | None = None
    sysut2_dsn: str | None = None
    sysut2_dataset: Dataset | None = None
    sysut2_sysout: bool = False
    sysin_data: str | None = None
    sysin_dummy: bool = False


def _gather_iebgener_info(step: Step) -> _IEBGenerInfo:
    info = _IEBGenerInfo()
    for dd in step.dds:
        name = get_dd_name(dd).upper()
        if name == "SYSUT1":
            if dd.datasets:
                ds = dd.datasets[0]
                if ds.path:
                    info.sysut1_path = ds.path
                else:
                    info.sysut1_dsn = ds.dsn
                info.sysut1_dataset = ds
            elif dd.instream is not None:
                info.sysut1_instream = dd.instream
        elif name == "SYSUT2":
            if dd.datasets:
                info.sysut2_dsn = dd.datasets[0].dsn
                info.sysut2_dataset = dd.datasets[0]
            elif dd.sysout:
                info.sysut2_sysout = True
    info.sysin_data = get_sysin(step)
    info.sysin_dummy = sysin_is_dummy(step)
    return info


# Each matcher inspects the gathered info and returns an intent (or
# None to defer to the next matcher). Order matters: more-specific
# patterns must come before more-general ones.


def _match_path_to_dsn(info: _IEBGenerInfo) -> CopyDataset | None:
    if info.sysut1_path and info.sysut2_dsn:
        return CopyDataset(src_path=info.sysut1_path, dest_dsn=info.sysut2_dsn)
    return None


def _match_path_to_sysout(info: _IEBGenerInfo) -> PathRead | None:
    """USS file → SYSOUT (job log). Each renderer picks its own form."""
    if info.sysut1_path and info.sysut2_sysout:
        return PathRead(path=info.sysut1_path)
    return None


def _match_instream_to_dsn(info: _IEBGenerInfo) -> CopyDataset | None:
    if info.sysut1_instream is not None and info.sysut2_dsn:
        return CopyDataset(
            instream=info.sysut1_instream,
            dest_dsn=info.sysut2_dsn,
            dest_dataset=info.sysut2_dataset,
        )
    return None


def _match_dsn_to_dsn(info: _IEBGenerInfo) -> CopyDataset | Fallback | None:
    if not (info.sysut1_dsn and info.sysut2_dsn):
        return None
    if info.sysin_dummy or not info.sysin_data:
        return CopyDataset(
            src_dsn=info.sysut1_dsn,
            dest_dsn=info.sysut2_dsn,
            src_dataset=info.sysut1_dataset,
            dest_dataset=info.sysut2_dataset,
        )
    # SYSIN has control statements: IEBGENER is filtering, not just copying.
    return Fallback(reason="IEBGENER: SYSIN has control statements")


def _match_dsn_to_sysout(info: _IEBGenerInfo) -> CopyDataset | None:
    if info.sysut1_dsn and info.sysut2_sysout:
        return CopyDataset(src_dsn=info.sysut1_dsn, to_sysout=True)
    return None


_IEBGENER_MATCHERS = (
    _match_path_to_dsn,
    _match_path_to_sysout,
    _match_instream_to_dsn,
    _match_dsn_to_dsn,
    _match_dsn_to_sysout,
)


def _classify_iebgener(step: Step) -> CopyDataset | PathRead | Fallback:
    info = _gather_iebgener_info(step)
    for matcher in _IEBGENER_MATCHERS:
        result = matcher(info)
        if result is not None:
            return result
    return Fallback(reason="IEBGENER: Missing SYSUT1 or SYSUT2")


def _classify_iebcopy(step: Step) -> CopyDataset | Fallback:
    sysin_data = get_sysin(step)
    dd_map = build_dd_map(step)

    if sysin_is_dummy(step) or not sysin_data:
        sysut1_dd = dd_map.get("SYSUT1")
        sysut2_dd = dd_map.get("SYSUT2")
        if sysut1_dd and sysut2_dd and sysut1_dd.datasets and sysut2_dd.datasets:
            return CopyDataset(
                src_dsn=sysut1_dd.datasets[0].dsn,
                dest_dsn=sysut2_dd.datasets[0].dsn,
            )

    if sysin_data:
        for line in sysin_data.strip().split("\n"):
            line_upper = line.strip().upper()
            if "COPY" in line_upper:
                outdd_match = re.search(r"OUTDD\s*=\s*([A-Z0-9]+)", line_upper)
                indd_match = re.search(r"INDD\s*=\s*(?:\(([A-Z0-9,]+)\)|([A-Z0-9]+))", line_upper)
                if outdd_match and indd_match:
                    out_name = outdd_match.group(1)
                    indd_val = indd_match.group(1) or indd_match.group(2)
                    in_names = [n.strip() for n in indd_val.split(",")]

                    out_dd = dd_map.get(out_name)
                    in_dds = [dd_map.get(n) for n in in_names]

                    if (
                        out_dd
                        and out_dd.datasets
                        and len(in_dds) == 1
                        and in_dds[0]
                        and in_dds[0].datasets
                    ):
                        return CopyDataset(
                            src_dsn=in_dds[0].datasets[0].dsn,
                            dest_dsn=out_dd.datasets[0].dsn,
                        )

    return Fallback(reason="IEBCOPY: Could not parse SYSIN control statements")


def _classify_idcams(
    step: Step,
) -> DeleteDatasets | DefineGDG | AlterRename | ListCatalog | Fallback:
    sysin_data = get_sysin(step)
    if not sysin_data:
        return Fallback(reason="IDCAMS: No SYSIN instream data")

    joined = _join_continuations(sysin_data)
    statements = [ln for ln in joined if not ln.strip().startswith("/*")]

    # Single-statement specializations (DEFINE GDG, ALTER ... NEWNAME).
    if len(statements) == 1:
        line = statements[0]
        upper = line.upper()

        if "DEFINE GENERATIONDATAGROUP" in upper:
            name_m = re.search(r"NAME\s*\(\s*([^)\s]+)\s*\)", upper)
            limit_m = re.search(r"LIMIT\s*\(\s*(\d+)\s*\)", upper)
            if name_m:
                return DefineGDG(
                    name=line[name_m.start(1) : name_m.end(1)],
                    limit=int(limit_m.group(1)) if limit_m else None,
                )

        alter_m = re.match(
            r"\s*ALTER\s+(\S+)\s+NEWNAME\s*\(\s*([^)]+?)\s*\)",
            upper,
        )
        if alter_m:
            return AlterRename(
                old_dsn=line[alter_m.start(1) : alter_m.end(1)],
                new_dsn=line[alter_m.start(2) : alter_m.end(2)],
            )

        # LISTCAT ENTRIES('dsn'[,'dsn'...]): existence check.
        entries_m = re.search(r"LISTCAT\s+ENTRIES\s*\(\s*([^)]+)\)", upper)
        if entries_m:
            raw = line[entries_m.start(1) : entries_m.end(1)]
            entries = [e.strip().strip("'\"") for e in raw.split(",") if e.strip()]
            return ListCatalog(entries=entries)

        # LISTCAT LVL(prefix) [...]: prefix listing.
        lvl_m = re.search(r"LISTCAT\s+(?:[A-Z]+\s+)*LVL\s*\(\s*([^)]+?)\s*\)", upper)
        if lvl_m:
            return ListCatalog(level=line[lvl_m.start(1) : lvl_m.end(1)])

    # Otherwise look for DELETE statements.
    delete_dsns: list[str] = []
    has_non_delete = False
    for line in statements:
        line_upper = line.strip().upper()
        if not line_upper or line_upper.startswith("SET "):
            continue
        if line_upper.startswith("DELETE"):
            parts = line_upper.split()
            if len(parts) >= 2:
                target = parts[1].strip("'\"")
                delete_dsns.append(target)
        else:
            has_non_delete = True

    if has_non_delete or not delete_dsns:
        return Fallback(reason="IDCAMS: Contains non-DELETE commands")

    return DeleteDatasets(dsns=delete_dsns)


def _classify_sort(step: Step) -> TextReplace | Fallback:
    sysin = get_sysin(step) or ""
    joined = " ".join(_join_continuations(sysin))
    upper = joined.upper()

    findrep = re.search(
        r"FINDREP\s*=\s*\(\s*IN\s*=\s*C'([^']*)'\s*,\s*OUT\s*=\s*C'([^']*)'",
        upper,
    )
    if not findrep:
        return Fallback(reason="SORT: No FINDREP clause")

    # Use the case-preserving original positions.
    find = joined[findrep.start(1) : findrep.end(1)]
    repl = joined[findrep.start(2) : findrep.end(2)]

    dd_map = build_dd_map(step)
    sortin = dd_map.get("SORTIN")
    if not (sortin and sortin.datasets):
        return Fallback(reason="SORT: Missing SORTIN dataset")

    return TextReplace(dsn=sortin.datasets[0].dsn, find=find, replace=repl)


def _classify_isrsupc(step: Step) -> TextSearch | Fallback:
    sysin = get_sysin(step) or ""
    joined = " ".join(_join_continuations(sysin))

    srch = re.search(r"SRCHFOR\s+'([^']+)'", joined, re.IGNORECASE)
    if not srch:
        # CMPCOLM/diff usage is handled by the existing _convert_isrsupc path.
        return Fallback(reason="ISRSUPC: No SRCHFOR pattern")

    pattern = srch.group(1)
    dd_map = build_dd_map(step)
    target = dd_map.get("NEWDD") or dd_map.get("OLDDD") or dd_map.get("INDD")
    if not (target and target.datasets):
        return Fallback(reason="ISRSUPC: SRCHFOR target DD missing")

    return TextSearch(dsn=target.datasets[0].dsn, pattern=pattern)


def _classify_tso(step: Step) -> TSOCommands | Fallback:
    tso_input = get_dd_instream(step, "SYSTSIN")
    if tso_input is None:
        tso_input = get_sysin(step)

    if tso_input is None:
        return Fallback(reason="IKJEFT01: No SYSTSIN or SYSIN instream data")

    commands = []
    for line in tso_input.strip().split("\n"):
        stripped = line.strip()
        if stripped and not stripped.startswith("/*"):
            commands.append(stripped)

    if not commands:
        return Fallback(reason="IKJEFT01: No TSO commands found")

    return TSOCommands(commands=commands)


def _classify_adrdssu(step: Step) -> BackupRestore | Fallback:
    sysin_data = get_sysin(step)
    if not sysin_data:
        return Fallback(reason="ADRDSSU: No SYSIN instream data")

    joined = []
    for line in sysin_data.strip().split("\n"):
        stripped = line.strip()
        if stripped.endswith(" -"):
            stripped = stripped[:-2].rstrip()
        joined.append(stripped)
    line_upper = " ".join(joined).upper()

    operation = None
    if "DUMP" in line_upper:
        operation = "dump"
    elif "RESTORE" in line_upper:
        operation = "restore"

    if not operation:
        return Fallback(reason="ADRDSSU: No DUMP or RESTORE command found")

    patterns: list[str] = []
    include_match = re.search(r"(?:INCLUDE|INC)\s*\(\s*([^)]+)\)", line_upper)
    if include_match:
        patterns = [p.strip().strip("'\" ") for p in include_match.group(1).split(",")]

    dd_map = build_dd_map(step)
    target_dsn = None

    # ADRDSSU accepts both OUTDD and OUTDDNAME (and INDD/INDDNAME).
    # The (?:NAME)? makes the longer form optional.
    outdd_match = re.search(r"OUTDD(?:NAME)?\s*\(\s*([A-Z0-9]+)\s*\)", line_upper)
    indd_match = re.search(r"INDD(?:NAME)?\s*\(\s*([A-Z0-9]+)\s*\)", line_upper)
    dd_name = outdd_match.group(1) if outdd_match else (indd_match.group(1) if indd_match else None)
    if dd_name and dd_name in dd_map:
        dd = dd_map[dd_name]
        if dd.datasets:
            target_dsn = dd.datasets[0].dsn

    return BackupRestore(
        operation=operation,
        patterns=patterns,
        target_dsn=target_dsn,
        replace="REPLACE" in line_upper,
    )


def _classify_bpxbatch(step: Step) -> ShellCommand | Fallback:
    cmd = _extract_bpxbatch_command(step)
    if cmd is None:
        return Fallback(reason="BPXBATCH: Could not extract shell command")

    env_lines: list[str] = []
    stdenv = get_dd_instream(step, "STDENV")
    if stdenv:
        for line in stdenv.strip().split("\n"):
            line = line.strip()
            if line and "=" in line and not line.startswith("#"):
                env_lines.append(line)

    return ShellCommand(
        cmd=cmd,
        env_lines=env_lines,
        stdin_path=_get_dd_path(step, "STDIN"),
        stdout_path=_get_dd_path(step, "STDOUT"),
        stderr_path=_get_dd_path(step, "STDERR"),
    )


def _extract_bpxbatch_command(step: Step) -> str | None:
    if step.parm:
        parm = strip_parm_quotes(step.parm)
        if parm.upper().startswith("SH "):
            return parm[3:].strip()

    if step.program and step.program.upper() == "BPXBATSL":
        stdparm = get_dd_instream(step, "STDPARM")
        if stdparm:
            cmd = stdparm.strip()
            if cmd.upper().startswith("SH "):
                return cmd[3:].strip()

    return None


def _get_dd_path(step: Step, target_dd: str) -> str | None:
    target_upper = target_dd.upper()
    for dd in step.dds:
        if get_dd_name(dd).upper() == target_upper and dd.datasets:
            dsn = dd.datasets[0].dsn
            if dsn.startswith("/"):
                return dsn
    return None


def _classify_iehlist(step: Step) -> IEHListOps | Fallback:
    sysin_data = get_sysin(step)
    if not sysin_data:
        return Fallback(reason="IEHLIST: No SYSIN control statements")

    pds_dsns: list[str] = []
    vtoc_volumes: list[str] = []

    for line in sysin_data.strip().split("\n"):
        line_upper = line.strip().upper()
        if line_upper.startswith("LISTPDS"):
            match = re.search(r"DSNAME\s*=\s*([A-Z0-9.$@#]+|\([^)]+\))", line_upper)
            if match:
                dsn = match.group(1).strip("()").split(",")[0].strip()
                pds_dsns.append(dsn)
        elif line_upper.startswith("LISTVTOC"):
            match = re.search(r"VOL(?:UME)?\s*=\s*[A-Z0-9]+\s*=\s*([A-Z0-9]+)", line_upper)
            if match:
                vtoc_volumes.append(match.group(1))

    if not pds_dsns and not vtoc_volumes:
        return Fallback(reason="IEHLIST: No convertible control statements")

    return IEHListOps(pds_dsns=pds_dsns, vtoc_volumes=vtoc_volumes)


def _classify_iehprogm(step: Step) -> IEHPROGMOps | Fallback:
    sysin_data = get_sysin(step)
    if not sysin_data:
        return Fallback(reason="IEHPROGM: No SYSIN control statements")

    renames: list[tuple[str, str, str | None]] = []
    scratches: list[tuple[str, str | None]] = []
    unsupported: list[str] = []

    for line in _join_continuations(sysin_data):
        line_upper = line.strip().upper()

        if line_upper.startswith("RENAME"):
            dsn_m = re.search(r"DSNAME\s*=\s*([A-Z0-9.$@#]+)", line_upper)
            new_m = re.search(r"NEWNAME\s*=\s*([A-Z0-9.$@#]+)", line_upper)
            mem_m = re.search(r"MEMBER\s*=\s*([A-Z0-9$@#]+)", line_upper)
            if dsn_m and new_m:
                renames.append(
                    (
                        dsn_m.group(1),
                        new_m.group(1),
                        mem_m.group(1) if mem_m else None,
                    )
                )

        elif line_upper.startswith("SCRATCH"):
            dsn_m = re.search(r"DSNAME\s*=\s*([A-Z0-9.$@#]+)", line_upper)
            mem_m = re.search(r"MEMBER\s*=\s*([A-Z0-9$@#]+)", line_upper)
            if dsn_m:
                scratches.append(
                    (
                        dsn_m.group(1),
                        mem_m.group(1) if mem_m else None,
                    )
                )

        elif line_upper.startswith(("CATLG", "UNCATLG", "BLDG")):
            unsupported.append(line_upper.split()[0])

    if unsupported:
        return Fallback(reason=f"IEHPROGM: {', '.join(set(unsupported))} requires mvscmd")

    if not renames and not scratches:
        return Fallback(reason="IEHPROGM: No convertible control statements")

    return IEHPROGMOps(renames=renames, scratches=scratches)


def _join_continuations(sysin_data: str) -> list[str]:
    """Join IDCAMS or IEHPROGM continuations on trailing comma or hyphen."""
    raw_lines = sysin_data.split("\n")
    joined: list[str] = []
    current = ""
    for raw in raw_lines:
        line = raw.rstrip()
        if line.endswith("+"):
            line = line[:-1].rstrip()
        if not line:
            if current:
                joined.append(current)
                current = ""
            continue

        ends_continued = line.endswith(",") or line.endswith("-")
        if current:
            # Trailing comma joins flush (parsers want the comma); trailing
            # dash inserts a space (IDCAMS treats line-break as whitespace).
            sep = "" if current.endswith(",") else " "
            current = current + sep + line.lstrip()
        else:
            current = line
        if ends_continued:
            # Drop the dash; commas stay because the parsers want them.
            if current.endswith("-"):
                current = current[:-1].rstrip()
        else:
            joined.append(current)
            current = ""

    if current:
        joined.append(current)
    return joined
