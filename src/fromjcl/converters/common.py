"""fromjcl/converters/common.py - Shared utilities for converters."""

from fromjcl.models import Step, DD, Dataset

# Programs known to require APF authorization (mvscmdauth)
# Users can add to this set for site-specific authorized programs
AUTHORIZED_PROGRAMS = {
    "IDCAMS",
    "IKJEFT01",   # Batch TSO
    "IKJEFT1B",   # Batch TSO alternate
    "ADRDSSU",    # DFSMSdss
    "ISFAFD",     # SDSF batch
    "ARCCTL",     # HSM
}

# Programs confirmed to NOT require authorization
UNAUTHORIZED_PROGRAMS = {
    "IEBCOPY",    # Changed to AC(0) in z/OS V1R13
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
    "ICEMAN",     # DFSORT
    "ISRSUPC",    # SuperC
}


def needs_authorization(program: str) -> bool | None:
    """Check if a program requires APF authorization.
    
    Returns:
        True - known to require mvscmdauth
        False - known to work with mvscmd
        None - unknown, user should try mvscmd first
    """
    if not program:
        return None
    pgm = program.upper()
    if pgm in AUTHORIZED_PROGRAMS:
        return True
    if pgm in UNAUTHORIZED_PROGRAMS:
        return False
    return None


def get_mvscmd_executable(program: str) -> str:
    """Return 'mvscmd' or 'mvscmdauth' based on program."""
    auth = needs_authorization(program)
    if auth is True:
        return "mvscmdauth"
    return "mvscmd"


def build_mvscmd_command(step: Step, force_auth: bool | None = None) -> list[str]:
    """Build mvscmd/mvscmdauth command for a step.
    
    Args:
        step: The step to convert
        force_auth: If True, use mvscmdauth. If False, use mvscmd.
                   If None, auto-detect based on program name.
    
    Returns:
        List of shell command lines
    """
    result = []
    parts = []
    instream_content = None
    steplib_datasets = []
    
    # Determine executable
    if force_auth is True:
        exe = "mvscmdauth"
    elif force_auth is False:
        exe = "mvscmd"
    else:
        exe = get_mvscmd_executable(step.program)
    
    parts.append(exe)
    
    if step.program:
        parts.append(f"--pgm={step.program}")
    elif step.proc:
        result.append(f"# WARNING: PROC={step.proc} cannot be executed by {exe}.")
        result.append(f"# Expand the PROC or find the program it calls.")
        parts.append("--pgm=UNKNOWN")
    
    if step.parm:
        parm = step.parm
        if parm.startswith("'") and parm.endswith("'"):
            parm = parm[1:-1]
        elif parm.startswith("('") and parm.endswith("')"):
            parm = parm[2:-2]
        parts.append(f"--args='{parm}'")
    
    for dd in step.dds:
        dd_name = dd.name.split(".")[-1] if "." in dd.name else dd.name
        dd_upper = dd_name.upper()
        dd_lower = dd_name.lower()
        
        # Handle STEPLIB/JOBLIB specially
        if dd_upper in ("STEPLIB", "JOBLIB"):
            if dd.datasets:
                for ds in dd.datasets:
                    steplib_datasets.append(ds.dsn)
            continue
        
        if dd.instream is not None:
            parts.append(f"--{dd_lower}=stdin")
            instream_content = dd.instream.rstrip("\n")
        elif dd.dummy:
            parts.append(f"--{dd_lower}=dummy")
        elif dd.sysout:
            parts.append(f"--{dd_lower}=*")
        elif dd.datasets:
            values = [format_dataset(ds) for ds in dd.datasets]
            parts.append(f"--{dd_lower}={':'.join(values)}")
    
    # Add steplib if present
    if steplib_datasets:
        parts.insert(2, f"--steplib={':'.join(steplib_datasets)}")
    
    # Build the command
    if len(parts) <= 2:
        cmd = " ".join(parts)
    else:
        cmd = parts[0] + " \\\n    " + " \\\n    ".join(parts[1:])
    
    # If we have instream data, use echo with pipe
    if instream_content is not None:
        cleaned = "\n".join(line.rstrip() for line in instream_content.split("\n"))
        escaped = cleaned.replace("'", "'\\''")
        result.append(f"echo '{escaped}' | {cmd}")
    else:
        result.append(cmd)
    
    return result


def format_dataset(ds: Dataset) -> str:
    """Format a dataset for mvscmd."""
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
            if ds.space.directory and ds_type and ds_type.lower() not in ("seq", "basic", "large"):
                parts.append(f"DIRBLKS={ds.space.directory}")
        
        if ds.volumes:
            parts.append(f"VOLUMES={','.join(ds.volumes)}")
        
        if ds.disposition.normal:
            parts.append(f"NORMDISP={map_disposition(ds.disposition.normal)}")
        if ds.disposition.abnormal:
            parts.append(f"CONDDISP={map_disposition(ds.disposition.abnormal)}")
    
    return ",".join(parts)


def map_disposition(disp: str) -> str:
    """Map JCL disposition to mvscmd disposition."""
    disp = disp.upper()
    if disp == "CATLG":
        return "CATALOG"
    elif disp == "UNCATLG":
        return "UNCATALOG"
    return disp.lower()