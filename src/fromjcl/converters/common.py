"""Shared utilities for the ZOAU / mvscmd shell converters."""

from fromjcl.models import DD, Dataset, Step

# Programs that require APF authorisation (typically because they issue
# SVCs that touch system control blocks). Under z/OS UNIX, these must
# run via mvscmdauth, which jumps into an authorised TCB. Plain mvscmd
# does not have the entitlement. Source: ZOAU 1.4 mvscmd manpage and
# the IBM z/OS Authorized Assembler Services Guide.
AUTHORIZED_PROGRAMS = {
    "IDCAMS",
    "IKJEFT01",
    "IKJEFT1B",
    "ADRDSSU",
    "ISFAFD",
    "ARCCTL",
}

# Utility programs known to run unauthorised. Listed explicitly so
# needs_authorization() can short-circuit to False instead of returning
# None (unknown), which would force a manual review of every converted
# step. Source: same as AUTHORIZED_PROGRAMS.
UNAUTHORIZED_PROGRAMS = {
    "IEBCOPY",
    "IEBGENER",
    "IEFBR14",
    "IEBCOMPR",
    "IEBDG",
    "IEBPTPCH",
    "IEBUPDTE",
    "IEHLIST",
    "IEHPROGM",
    "IEHMOVE",
    "SORT",
    "ICEMAN",
    "ISRSUPC",
}


def needs_authorization(program: str) -> bool | None:
    """True = mvscmdauth, False = mvscmd, None = unknown."""
    if not program:
        return None
    pgm = program.upper()
    if pgm in AUTHORIZED_PROGRAMS:
        return True
    if pgm in UNAUTHORIZED_PROGRAMS:
        return False
    return None


def resolve_symbols(value: str, symbols: dict[str, str]) -> str:
    """Substitute &SYMBOL and &SYMBOL. references in value."""
    if not value or not symbols:
        return value
    result = value
    for sym, replacement in symbols.items():
        result = result.replace(f"&{sym}.", replacement)
        result = result.replace(f"&{sym}", replacement)
    return result


def get_dd_name(dd: DD) -> str:
    """Return the DD's local name, stripped of any PROC. prefix."""
    return dd.name.split(".")[-1] if "." in dd.name else dd.name


def get_sysin(step: Step) -> str | None:
    """Return the SYSIN DD's instream text, or None if no SYSIN."""
    return get_dd_instream(step, "SYSIN")


def get_dd_instream(step: Step, target_dd: str) -> str | None:
    """Return the named DD's instream text, or None if no match."""
    target_upper = target_dd.upper()
    for dd in step.dds:
        if get_dd_name(dd).upper() == target_upper and dd.instream is not None:
            return dd.instream
    return None


def build_dd_map(step: Step) -> dict[str, DD]:
    """Index a step's DDs by uppercase name."""
    return {get_dd_name(dd).upper(): dd for dd in step.dds}


def sysin_is_dummy(step: Step) -> bool:
    """True when the step has a SYSIN DD DUMMY."""
    return any(get_dd_name(dd).upper() == "SYSIN" and dd.dummy for dd in step.dds)


def _resolve_executable(step: Step, force_auth: bool | None) -> str:
    auth = force_auth if force_auth is not None else needs_authorization(step.program or "")
    return "mvscmdauth" if auth is True else "mvscmd"


def strip_parm_quotes(parm: str) -> str:
    """Strip the outer quotes from a JCL PARM= value."""
    if parm.startswith("'") and parm.endswith("'"):
        return parm[1:-1]
    if parm.startswith("('") and parm.endswith("')"):
        return parm[2:-2]
    return parm


def _format_dd_arg(dd: DD) -> str | None:
    """Render a single DD as --<name>=<value>. Returns None for
    STEPLIB/JOBLIB (handled separately) and DDs we can't translate."""
    dd_name = get_dd_name(dd)
    dd_lower = dd_name.lower()
    if dd_name.upper() in ("STEPLIB", "JOBLIB"):
        return None
    if dd.instream is not None:
        return f"--{dd_lower}=stdin"
    if dd.dummy:
        return f"--{dd_lower}=dummy"
    if dd.sysout:
        return f"--{dd_lower}=*"
    if dd.datasets:
        values = [format_dataset(ds) for ds in dd.datasets]
        return _shell_safe_arg(f"--{dd_lower}=", ":".join(values))
    return None


def _collect_steplib(step: Step) -> list[str]:
    """All datasets concatenated under STEPLIB/JOBLIB DDs."""
    out: list[str] = []
    for dd in step.dds:
        if get_dd_name(dd).upper() in ("STEPLIB", "JOBLIB") and dd.datasets:
            out.extend(ds.dsn for ds in dd.datasets)
    return out


def _format_command_line(parts: list[str]) -> str:
    """Join mvscmd --x ... --y ... over multiple lines if there's more
    than just mvscmd --pgm=X."""
    if len(parts) <= 2:
        return " ".join(parts)
    return parts[0] + " \\\n    " + " \\\n    ".join(parts[1:])


def build_mvscmd_command(step: Step, force_auth: bool | None = None) -> list[str]:
    """Render step as an mvscmd or mvscmdauth invocation."""
    result: list[str] = []
    exe = _resolve_executable(step, force_auth)
    parts: list[str] = [exe]

    if step.program:
        parts.append(f"--pgm={step.program}")
    elif step.proc:
        result.append(f"# WARNING: PROC={step.proc} cannot be executed by {exe}.")
        result.append("# Expand the PROC or find the program it calls.")
        parts.append("--pgm=UNKNOWN")

    if step.parm:
        parts.append(f"--args='{strip_parm_quotes(step.parm)}'")

    instream_content: str | None = None
    for dd in step.dds:
        arg = _format_dd_arg(dd)
        if arg is not None:
            parts.append(arg)
        if dd.instream is not None and get_dd_name(dd).upper() not in ("STEPLIB", "JOBLIB"):
            instream_content = dd.instream.rstrip("\n")

    steplib_datasets = _collect_steplib(step)
    if steplib_datasets:
        # Insert at index 2: after `mvscmd` (0) and `--pgm=X` (1) but
        # before any user-DD --foo=bar args. mvscmd resolves STEPLIB
        # before opening DDs, so the position only matters for human
        # readability; we put it up front so a reviewer sees the
        # library context immediately.
        parts.insert(2, _shell_safe_arg("--steplib=", ":".join(steplib_datasets)))

    cmd = _format_command_line(parts)
    if instream_content is not None:
        cleaned = "\n".join(line.rstrip() for line in instream_content.split("\n"))
        escaped = cleaned.replace("'", "'\\''")
        result.append(f"echo '{escaped}' | {cmd}")
    else:
        result.append(cmd)
    return result


def _shell_safe_arg(prefix: str, value: str) -> str:
    """Single-quote value if it contains shell metacharacters."""
    if any(c in value for c in "()[]{};&|<>$*?` "):
        escaped = value.replace("'", "'\\''")
        return f"{prefix}'{escaped}'"
    return f"{prefix}{value}"


def format_dataset(ds: Dataset) -> str:
    """Render a dataset as a comma-joined mvscmd argument value."""
    parts = [ds.dsn]
    status = ds.disposition.status.upper()

    if status == "OLD":
        parts.append("EXCL")
    elif status == "MOD":
        parts.append("MOD")
    elif status == "NEW":
        parts.append("NEW")

        ds_type = ds.dataset_type
        if ds_type:
            parts.append(f"TYPE={ds_type.lower()}")

        if ds.dcb:
            if ds.dcb.recfm:
                parts.append(f"RECFM={ds.dcb.recfm}")
            if ds.dcb.lrecl:
                parts.append(f"LRECL={ds.dcb.lrecl}")
            if ds.dcb.blksize:
                parts.append(f"BLKSIZE={ds.dcb.blksize}")

        if ds.space:
            stype = ds.space.type.upper()
            parts.append(f"PRIMARY={ds.space.primary}{stype}")
            if ds.space.secondary:
                parts.append(f"SECONDARY={ds.space.secondary}{stype}")
            # DIRBLKS only meaningful for PDS/PDSE — sequential and
            # large-format datasets have no directory, so JCL allows
            # the (...,dir) third SPACE arg but mvscmd would reject it.
            if ds.space.directory and ds_type and ds_type.lower() not in ("seq", "basic", "large"):
                parts.append(f"DIRBLKS={ds.space.directory}")

        if ds.volumes:
            parts.append(f"VOLUMES={','.join(ds.volumes)}")

        if ds.disposition.normal:
            parts.append(f"NORMDISP={_map_mvscmd_disposition(ds.disposition.normal)}")
        if ds.disposition.abnormal:
            parts.append(f"CONDDISP={_map_mvscmd_disposition(ds.disposition.abnormal)}")

    return ",".join(parts)


def _map_mvscmd_disposition(disp: str) -> str:
    disp = disp.upper()
    if disp == "CATLG":
        return "CATALOG"
    elif disp == "UNCATLG":
        return "UNCATALOG"
    return disp.lower()
