# SPDX-License-Identifier: Apache-2.0
"""Reverse path: load a yaml/json/csv dump of a Job and emit JCL.

The forward path is parser.parse() then serialize/<fmt>. The yaml and json
serialisers dump the Job model (semantic, not byte-exact). This module
takes that semantic dump back to JCL by synthesising a parsed-statement
list and feeding it through serialize.jcl, which already handles emission
when no record metadata is present.

Output is functionally equivalent JCL, not byte-exact. The original
column layout, comments, and formatting are not preserved by the Job
model and so cannot be reconstructed here.
"""

from __future__ import annotations

import csv as _csv
import io
import json as _json
from typing import Any

import yaml as _yaml

from fromjcl.serialize import jcl as jcl_out


def detect_format(text: str) -> str:
    """Sniff yaml/json/csv from the leading bytes."""
    s = text.lstrip()
    if s.startswith(("{", "[")):
        return "json"
    first_line = s.split("\n", 1)[0].strip()
    if first_line.startswith("job,") and "step" in first_line:
        return "csv"
    return "yaml"


def convert(text: str, fmt: str | None = None) -> str:
    """Convert a yaml/json/csv Job dump back to JCL text."""
    fmt = fmt or detect_format(text)
    if fmt == "json":
        job_dict = _json.loads(text)
    elif fmt == "yaml":
        job_dict = _yaml.safe_load(text)
    elif fmt == "csv":
        job_dict = _job_dict_from_csv(text)
    else:
        raise ValueError(f"unsupported rejcl input format: {fmt}")

    if not isinstance(job_dict, dict):
        raise ValueError("rejcl input did not parse to a Job mapping")

    parsed = _job_dict_to_parsed(job_dict)
    return jcl_out.convert(parsed)


def _job_dict_from_csv(text: str) -> dict[str, Any]:
    # JOB-level fields repeat on every row; first non-empty wins.
    reader = _csv.DictReader(io.StringIO(text))
    job: dict[str, Any] = {"name": "UNNAMED"}
    steps: dict[str, dict[str, Any]] = {}
    step_order: list[str] = []
    for row in reader:
        if row.get("job"):
            job["name"] = row["job"]
        for src, dst in (
            ("account", "account"),
            ("programmer", "programmer"),
            ("class", "class_"),
            ("msgclass", "msgclass"),
            ("msglevel", "msglevel"),
            ("notify", "notify"),
        ):
            if row.get(src) and not job.get(dst):
                job[dst] = row[src]
        if row.get("symbols") and not job.get("symbols"):
            # Inverse of serialize/csv.py:_step_base symbols encoding.
            job["symbols"] = dict(
                pair.split("=", 1) for pair in row["symbols"].split(";") if "=" in pair
            )
        step_name = row.get("step") or ""
        if step_name not in steps:
            steps[step_name] = {
                "name": step_name,
                "program": row.get("program") or None,
                "proc": row.get("proc") or None,
                "parm": row.get("parm") or None,
                "region": row.get("region") or None,
                "cond": row.get("cond") or None,
                "condition": row.get("condition") or None,
                "dds": [],
            }
            step_order.append(step_name)
        step = steps[step_name]

        dd_name = row.get("dd") or ""
        if not dd_name:
            continue

        last_dd = step["dds"][-1] if step["dds"] else None
        if last_dd is None or last_dd.get("name") != dd_name:
            dd: dict[str, Any] = {"name": dd_name}
            if row.get("sysout"):
                dd["sysout"] = row["sysout"]
            elif row.get("dummy"):
                dd["dummy"] = True
            elif row.get("instream"):
                # Inverse of serialize/csv.py:_format_instream.
                dd["instream"] = row["instream"].replace("\\n", "\n")
            else:
                dd["datasets"] = []
            step["dds"].append(dd)
            last_dd = dd

        if "datasets" in last_dd and (row.get("dsn") or row.get("path")):
            ds: dict[str, Any] = {"dsn": row.get("dsn") or ""}
            if row.get("path"):
                ds["path"] = row["path"]
            disp: dict[str, Any] = {}
            if row.get("disp"):
                disp["status"] = row["disp"]
            if row.get("disp_normal"):
                disp["normal"] = row["disp_normal"]
            if row.get("disp_abnormal"):
                disp["abnormal"] = row["disp_abnormal"]
            if disp:
                ds["disposition"] = disp
            dcb: dict[str, Any] = {}
            if row.get("recfm"):
                dcb["recfm"] = row["recfm"]
            if row.get("lrecl"):
                dcb["lrecl"] = int(row["lrecl"])
            if row.get("blksize"):
                dcb["blksize"] = int(row["blksize"])
            if row.get("dsorg"):
                dcb["dsorg"] = row["dsorg"]
            if dcb:
                ds["dcb"] = dcb
            if row.get("space_type"):
                space: dict[str, Any] = {
                    "type": row["space_type"],
                    "primary": int(row.get("space_primary") or 0),
                }
                if row.get("space_secondary"):
                    space["secondary"] = int(row["space_secondary"])
                if row.get("space_directory"):
                    space["directory"] = int(row["space_directory"])
                ds["space"] = space
            if row.get("unit"):
                ds["unit"] = row["unit"]
            if row.get("volumes"):
                ds["volumes"] = [v for v in row["volumes"].split(",") if v]
            last_dd["datasets"].append(ds)

    job["steps"] = [steps[n] for n in step_order]
    return job


def _job_dict_to_parsed(job: dict[str, Any]) -> dict[str, Any]:
    statements: list[dict[str, Any]] = [_job_statement(job)]

    if job.get("symbols"):
        params = [{"key": k, "value": v} for k, v in job["symbols"].items()]
        statements.append({"type": "SET", "name": "", "parameters": params})

    for step in job.get("steps") or []:
        cond_text = step.get("condition")
        if cond_text:
            statements.append(
                {
                    "type": "IF",
                    "name": "",
                    "parameters": [],
                    "conditional": {"text": cond_text},
                }
            )
        statements.append(_exec_statement(step))
        for dd in step.get("dds") or []:
            statements.extend(_dd_statements(dd))
        if cond_text:
            statements.append({"type": "ENDIF", "name": "", "parameters": []})

    return {"statements": statements}


def _job_statement(job: dict[str, Any]) -> dict[str, Any]:
    params: list[dict[str, Any]] = []
    if job.get("account"):
        params.append({"key": job["account"], "value": None})
    if job.get("programmer"):
        params.append({"key": f"'{job['programmer']}'", "value": None})
    for src, dst in (
        ("class_", "CLASS"),
        ("msgclass", "MSGCLASS"),
        ("msglevel", "MSGLEVEL"),
        ("notify", "NOTIFY"),
    ):
        v = job.get(src)
        if v is not None and v != "":
            params.append({"key": dst, "value": v})
    return {"type": "JOB", "name": job.get("name") or "", "parameters": params}


def _exec_statement(step: dict[str, Any]) -> dict[str, Any]:
    params: list[dict[str, Any]] = []
    if step.get("program"):
        params.append({"key": "PGM", "value": step["program"]})
    elif step.get("proc"):
        params.append({"key": "PROC", "value": step["proc"]})

    param_map = {"parm": "PARM", "region": "REGION", "cond": "COND"}
    for key in step:
        if key in param_map:
            v = step[key]
            if v is not None and v != "":
                params.append({"key": param_map[key], "value": v})

    return {"type": "EXEC", "name": step.get("name") or "", "parameters": params}


def _dd_statements(dd: dict[str, Any]) -> list[dict[str, Any]]:
    name = dd.get("name") or ""
    if dd.get("sysout") is not None:
        return [
            {
                "type": "DD",
                "name": name,
                "parameters": [{"key": "SYSOUT", "value": dd["sysout"]}],
            }
        ]
    if dd.get("dummy"):
        return [
            {
                "type": "DD",
                "name": name,
                "parameters": [{"key": "DUMMY", "value": None}],
            }
        ]
    if dd.get("instream") is not None:
        # TODO: hardcoded `/*`. Custom DLM= is dropped on the forward pass.
        return [
            {
                "type": "DD",
                "name": name,
                "parameters": [{"key": "*", "value": None}],
                "instream": {"bytes": dd["instream"], "retain_delim": "/*"},
            }
        ]
    datasets = dd.get("datasets") or []
    if not datasets:
        return [{"type": "DD", "name": name, "parameters": []}]
    return [
        {"type": "DD", "name": name if i == 0 else "", "parameters": _dataset_params(ds)}
        for i, ds in enumerate(datasets)
    ]


def _dataset_params(ds: dict[str, Any]) -> list[dict[str, Any]]:
    params: list[dict[str, Any]] = []
    if ds.get("dsn"):
        params.append({"key": "DSN", "value": ds["dsn"]})
    if ds.get("path"):
        params.append({"key": "PATH", "value": f"'{ds['path']}'"})
    disp = ds.get("disposition")
    if disp and not _is_default_disp(disp):
        params.append({"key": "DISP", "value": _format_disp(disp)})
    if ds.get("space"):
        params.append({"key": "SPACE", "value": _format_space(ds["space"])})
    if ds.get("dcb"):
        params.append({"key": "DCB", "value": _format_dcb(ds["dcb"])})
    if ds.get("unit"):
        params.append({"key": "UNIT", "value": ds["unit"]})
    if ds.get("volumes"):
        vols = list(ds["volumes"])
        ser = vols[0] if len(vols) == 1 else f"({','.join(vols)})"
        params.append({"key": "VOL", "value": f"SER={ser}"})
    return params


def _is_default_disp(disp: dict[str, Any]) -> bool:
    return (
        (disp.get("status") or "SHR") == "SHR"
        and not disp.get("normal")
        and not disp.get("abnormal")
    )


def _format_disp(disp: dict[str, Any]) -> str:
    status = disp.get("status") or "SHR"
    normal = disp.get("normal") or ""
    abnormal = disp.get("abnormal") or ""
    if not normal and not abnormal:
        return status
    parts = [status, normal, abnormal]
    while parts and not parts[-1]:
        parts.pop()
    return f"({','.join(parts)})"


def _format_space(sp: dict[str, Any]) -> str:
    typ = sp.get("type") or "TRK"
    nums = [str(sp.get("primary") or 0)]
    if sp.get("secondary") is not None:
        nums.append(str(sp["secondary"]))
    if sp.get("directory") is not None:
        if len(nums) == 1:
            nums.append("0")
        nums.append(str(sp["directory"]))
    return f"({typ},({','.join(nums)}))"


def _format_dcb(dcb: dict[str, Any]) -> str:
    parts: list[str] = []
    for k in ("recfm", "lrecl", "blksize", "dsorg"):
        v = dcb.get(k)
        if v is not None and v != "":
            parts.append(f"{k.upper()}={v}")
    if len(parts) == 1:
        return parts[0]
    return f"({','.join(parts)})"
