# SPDX-License-Identifier: Apache-2.0
"""Convert JCL steps to ZOAU 1.4 shell commands."""

import re

from fromjcl.converters.classify import (
    AlterRename,
    BackupRestore,
    CopyDataset,
    DatasetOps,
    DefineGDG,
    DeleteDatasets,
    Fallback,
    IEHListOps,
    IEHPROGMOps,
    ListCatalog,
    PathRead,
    ShellCommand,
    TextReplace,
    TextSearch,
    TSOCommands,
    classify_step,
)
from fromjcl.converters.common import (
    build_mvscmd_command,
    get_dd_name,
    get_sysin,
    resolve_symbols,
)
from fromjcl.converters.shell import _scaffold
from fromjcl.models import Dataset, Job, Step


def convert(job: Job) -> str:
    """Render the job as a ZOAU shell script."""
    return _scaffold.emit(job, lambda step: _convert_step(step, job), header_tag="zoau")


def _convert_step(step: Step, job: Job) -> list[str]:
    pgm = (step.program or "").upper()
    intent = classify_step(step)

    # SRCHFOR maps to dgrep via the classifier; CMPCOLM falls through to ddiff here.
    if pgm == "ISRSUPC" and not isinstance(intent, TextSearch):
        return _convert_isrsupc(step)

    sym = job.symbols

    if isinstance(intent, DatasetOps):
        return _render_dataset_ops(intent, sym)
    if isinstance(intent, CopyDataset):
        return _render_copy(intent, sym)
    if isinstance(intent, DeleteDatasets):
        return _render_deletes(intent, sym)
    if isinstance(intent, DefineGDG):
        return _render_define_gdg(intent, sym)
    if isinstance(intent, AlterRename):
        return _render_alter_rename(intent, sym)
    if isinstance(intent, TextReplace):
        return _render_text_replace(intent, sym)
    if isinstance(intent, TextSearch):
        return _render_text_search(intent, sym)
    if isinstance(intent, ListCatalog):
        return _render_listcat(intent, sym)
    if isinstance(intent, TSOCommands):
        return _render_tso(intent, sym)
    if isinstance(intent, ShellCommand):
        return _render_shell(intent, sym)
    if isinstance(intent, PathRead):
        return [f'cat "{intent.path}"']
    if isinstance(intent, BackupRestore):
        return _render_backup(intent, sym)
    if isinstance(intent, IEHListOps):
        return _render_iehlist(intent)
    if isinstance(intent, IEHPROGMOps):
        return _render_iehprogm(intent)
    if isinstance(intent, Fallback):
        return _fallback(step, intent.reason)

    return _fallback(step, f"No ZOAU equivalent for {pgm}")


def _render_dataset_ops(intent: DatasetOps, sym: dict[str, str]) -> list[str]:
    result: list[str] = []
    for dd_name, dataset in intent.creates:
        dsn = resolve_symbols(dataset.dsn, sym)
        result.extend((f"# DD {dd_name}: Allocate dataset", _build_dtouch(dataset, dsn)))
    for raw_dsn in intent.deletes:
        dsn = resolve_symbols(raw_dsn, sym)
        result.extend(("# Delete dataset", f'drm "{dsn}"'))
    if not result:
        result.append("# IEFBR14 with no actionable DDs")
    return result


def _render_copy(intent: CopyDataset, sym: dict[str, str]) -> list[str]:
    if intent.src_path and intent.dest_dsn:
        path = resolve_symbols(intent.src_path, sym)
        dest = resolve_symbols(intent.dest_dsn, sym)
        return [f'dcp {path} "{dest}"']

    if intent.instream is not None and intent.dest_dsn:
        dest = resolve_symbols(intent.dest_dsn, sym)
        # decho's two-arg form takes the text directly: decho "<text>" "<dsn>".
        # Lines are joined with single spaces to match IBM's canonical example.
        joined = " ".join(line.strip() for line in intent.instream.split("\n") if line.strip())
        escaped = joined.replace("\\", "\\\\").replace('"', '\\"')
        return [f'decho "{escaped}" "{dest}"']

    if intent.src_dsn and intent.dest_dsn:
        src = resolve_symbols(intent.src_dsn, sym)
        dest = resolve_symbols(intent.dest_dsn, sym)
        return [f'dcp "{src}" "{dest}"']

    if intent.src_dsn and intent.to_sysout:
        src = resolve_symbols(intent.src_dsn, sym)
        return [f'dcat "{src}"']

    return ["# IEBGENER: Could not determine copy operation"]


def _render_deletes(intent: DeleteDatasets, sym: dict[str, str]) -> list[str]:
    result: list[str] = []
    for dsn in intent.dsns:
        dsn = resolve_symbols(dsn, sym)
        # DSN(MEMBER) becomes mrm (delete a PDS member, not the dataset).
        verb = "mrm" if dsn.endswith(")") and "(" in dsn else "drm"
        result.append(f'{verb} "{dsn}"')
    return result


def _render_define_gdg(intent: DefineGDG, sym: dict[str, str]) -> list[str]:
    name = resolve_symbols(intent.name, sym)
    if intent.limit is not None:
        return [f"dtouch -tGDG -L{intent.limit} {name}"]
    return [f"dtouch -tGDG {name}"]


def _render_alter_rename(intent: AlterRename, sym: dict[str, str]) -> list[str]:
    old = resolve_symbols(intent.old_dsn, sym)
    new = resolve_symbols(intent.new_dsn, sym)
    return [f'dmv "{old}" "{new}"']


def _render_text_replace(intent: TextReplace, sym: dict[str, str]) -> list[str]:
    dsn = resolve_symbols(intent.dsn, sym)
    # Forward slashes inside the find/replace need escaping for sed.
    find = intent.find.replace("/", r"\/")
    repl = intent.replace.replace("/", r"\/")
    return [f'dsed "s/{find}/{repl}/g" "{dsn}"']


def _render_text_search(intent: TextSearch, sym: dict[str, str]) -> list[str]:
    dsn = resolve_symbols(intent.dsn, sym)
    return [f'dgrep "{intent.pattern}" "{dsn}"']


def _render_listcat(intent: ListCatalog, sym: dict[str, str]) -> list[str]:
    if intent.entries:
        # Existence check: discard output, exit code carries the result.
        return [f'dls "{resolve_symbols(e, sym)}" 2>/dev/null >/dev/null' for e in intent.entries]
    if intent.level:
        prefix = resolve_symbols(intent.level, sym)
        return [f'dls -us "{prefix}.*"']
    return ["# LISTCAT: no ENTRIES or LVL"]


def _render_tso(intent: TSOCommands, sym: dict[str, str]) -> list[str]:
    # The PROFILE command alone is the canonical "print current HLQ"
    # idiom; ZOAU exposes this as the hlq shell utility.
    if len(intent.commands) == 1 and intent.commands[0].strip().upper() == "PROFILE":
        return ["hlq"]

    result: list[str] = []
    for cmd in intent.commands:
        cmd = resolve_symbols(cmd, sym)
        escaped = cmd.replace("'", "'\\''")
        result.append(f"tsocmd '{escaped}'")
    return result


def _render_shell(intent: ShellCommand, sym: dict[str, str]) -> list[str]:
    cmd = resolve_symbols(intent.cmd, sym)
    result: list[str] = []

    if intent.env_lines:
        for line in intent.env_lines:
            result.append(f"export {line}")
        result.append("")

    redirects = ""
    if intent.stdin_path:
        redirects += f" < {intent.stdin_path}"
    if intent.stdout_path:
        redirects += f" > {intent.stdout_path}"
    if intent.stderr_path:
        redirects += f" 2> {intent.stderr_path}"

    result.append(cmd + redirects)
    return result


def _render_backup(intent: BackupRestore, sym: dict[str, str]) -> list[str]:
    target = resolve_symbols(intent.target_dsn, sym) if intent.target_dsn else None

    if intent.operation == "dump":
        if not target:
            return ["# ADRDSSU DUMP: Cannot determine output dataset"]
        result: list[str] = []
        args = [f'-D "{target}"']
        for p in intent.patterns:
            args.append(f'"{p}"')
        if not intent.patterns:
            result.append("# WARNING: No INCLUDE patterns")
        result.append(f"dzip {' '.join(args)}")
        return result

    if intent.operation == "restore":
        if not target:
            return ["# ADRDSSU RESTORE: Cannot determine input dataset"]
        args = [f'-D "{target}"']
        if intent.replace:
            args.append("-o")
        return [f"dunzip {' '.join(args)}"]

    return ["# ADRDSSU: Unknown operation"]


def _convert_isrsupc(step: Step) -> list[str]:
    newdd = olddd = None
    sysin_data = get_sysin(step)

    for dd in step.dds:
        name = get_dd_name(dd).upper()
        if name == "NEWDD" and dd.datasets:
            newdd = dd.datasets[0].dsn
        elif name == "OLDDD" and dd.datasets:
            olddd = dd.datasets[0].dsn

    if not newdd or not olddd:
        return _fallback(step, "ISRSUPC: Missing NEWDD or OLDDD")

    opts = []
    if sysin_data:
        match = re.search(r"CMPCOLM[NO]?\s+(\d+):(\d+)", sysin_data.upper())
        if match:
            opts.append(f"-c{match.group(1)}:{match.group(2)}")

    opts_str = " ".join(opts)
    cmd = f'ddiff {opts_str} "{newdd}" "{olddd}"' if opts_str else f'ddiff "{newdd}" "{olddd}"'
    return [cmd]


def _render_iehlist(intent: IEHListOps) -> list[str]:
    return [
        *(f'mls "{dsn}"' for dsn in intent.pds_dsns),
        *(f"vtocls {vol}" for vol in intent.vtoc_volumes),
    ]


def _render_iehprogm(intent: IEHPROGMOps) -> list[str]:
    result: list[str] = []
    for dsn, newname, member in intent.renames:
        if member:
            result.append(f'mmv "{dsn}" {member} {newname}')
        else:
            result.append(f'dmv "{dsn}" "{newname}"')
    for dsn, member in intent.scratches:
        if member:
            result.append(f'mrm "{dsn}({member})"')
        else:
            result.append(f'drm "{dsn}"')
    return result


def _build_dtouch(ds: Dataset, dsn: str) -> str:
    args: list[str] = []

    if ds.dataset_type:
        # JCL BASIC sequential maps to -tseq. Unknown types default to PDSE.
        type_map = {"SEQ": "seq", "PDS": "pds", "PDSE": "pdse", "BASIC": "seq", "LARGE": "large"}
        args.append(f"-t{type_map.get(ds.dataset_type.upper(), 'pdse')}")

    if ds.dcb:
        if ds.dcb.lrecl:
            args.append(f"-l{ds.dcb.lrecl}")
        if ds.dcb.recfm:
            args.append(f"-r{ds.dcb.recfm}")
        if ds.dcb.blksize:
            args.append(f"-B{ds.dcb.blksize}")

    if ds.space:
        type_map = {"TRK": "T", "CYL": "C", "KB": "K", "MB": "M"}
        args.append(f"-s{ds.space.primary}{type_map.get(ds.space.type.upper(), 'T')}")

    if ds.volumes:
        args.append(f"-V{','.join(ds.volumes)}")

    args_str = " ".join(args)
    return f'dtouch {args_str} "{dsn}"' if args_str else f'dtouch "{dsn}"'


def _fallback(step: Step, reason: str) -> list[str]:
    result = [f"# Fallback: {reason}"]
    result.extend(build_mvscmd_command(step))
    return result
