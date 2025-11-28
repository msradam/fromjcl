"""Convert Job model to Ansible playbook using zos_mvs_raw."""

import yaml
from fromjcl.models import Job, Step, DD, Dataset


def convert(job: Job) -> str:
    """Convert Job to Ansible playbook."""
    tasks = []

    for step in job.steps:
        task = _build_task(step, job)
        if task:
            tasks.append(task)

    playbook = [
        {
            "name": f"Execute JCL job {job.name}",
            "hosts": "zos_host",
            "gather_facts": False,
            "tasks": tasks,
        }
    ]

    return yaml.dump(
        playbook, default_flow_style=False, sort_keys=False, allow_unicode=True
    )


def _build_task(step: Step, job: Job) -> dict | None:
    """Build an Ansible task for a step."""
    if step.proc:
        return {
            "name": f"Step {step.name} - PROC {step.proc} (requires manual conversion)",
            "ansible.builtin.debug": {
                "msg": f"PROC {step.proc} requires manual expansion",
            },
        }

    if not step.program:
        return None

    task = {
        "name": f"Step {step.name} - {step.program}",
        "ibm.ibm_zos_core.zos_mvs_raw": {
            "program_name": step.program,
        },
    }

    mvs_raw = task["ibm.ibm_zos_core.zos_mvs_raw"]

    if step.parm:
        parm = step.parm
        if parm.startswith("'") and parm.endswith("'"):
            parm = parm[1:-1]
        elif parm.startswith("('") and parm.endswith("')"):
            parm = parm[2:-2]
        mvs_raw["parm"] = parm

    dds = []
    for dd in step.dds:
        dd_entry = _build_dd(dd, job)
        if dd_entry:
            dds.append(dd_entry)

    if dds:
        mvs_raw["dds"] = dds

    return task


def _build_dd(dd: DD, job: Job) -> dict | None:
    """Build a DD entry for zos_mvs_raw."""
    dd_name = dd.name.split(".")[-1] if "." in dd.name else dd.name

    if dd.dummy:
        return {"dd_dummy": {"dd_name": dd_name}}

    if dd.sysout:
        return {"dd_output": {"dd_name": dd_name, "return_content": {"type": "text"}}}

    if dd.instream is not None:
        content = "\n".join(
            line.rstrip() for line in dd.instream.rstrip("\n").split("\n")
        )
        return {"dd_input": {"dd_name": dd_name, "content": content}}

    if dd.datasets:
        if len(dd.datasets) > 1:
            return _build_dd_concat(dd_name, dd.datasets, job)
        else:
            return _build_dd_data_set(dd_name, dd.datasets[0], job)

    return None


def _build_dd_data_set(dd_name: str, ds: Dataset, job: Job) -> dict:
    """Build a dd_data_set entry."""
    entry = {
        "dd_name": dd_name,
        "data_set_name": _resolve_symbols(ds.dsn, job.symbols),
        "disposition": ds.disposition.status.lower(),
    }

    if ds.disposition.normal:
        entry["disposition_normal"] = _map_disp_action(ds.disposition.normal)
    if ds.disposition.abnormal:
        entry["disposition_abnormal"] = _map_disp_action(ds.disposition.abnormal)

    if ds.disposition.status.upper() == "NEW":
        ds_type = ds.dataset_type
        if ds_type:
            entry["type"] = ds_type.lower()

        if ds.space:
            entry["space_type"] = ds.space.type.lower()
            entry["space_primary"] = ds.space.primary
            if ds.space.secondary:
                entry["space_secondary"] = ds.space.secondary
            if ds.space.directory:
                entry["directory_blocks"] = ds.space.directory

        if ds.volumes:
            entry["volumes"] = ds.volumes

    if ds.dcb:
        if ds.dcb.recfm:
            entry["record_format"] = ds.dcb.recfm.lower()
        if ds.dcb.lrecl:
            entry["record_length"] = ds.dcb.lrecl
        if ds.dcb.blksize:
            entry["block_size"] = ds.dcb.blksize

    return {"dd_data_set": entry}


def _build_dd_concat(dd_name: str, datasets: list[Dataset], job: Job) -> dict:
    """Build a dd_concat entry for concatenated datasets."""
    concat_dds = []

    for ds in datasets:
        entry = {"data_set_name": _resolve_symbols(ds.dsn, job.symbols)}
        if ds.disposition.status.upper() != "SHR":
            entry["disposition"] = ds.disposition.status.lower()
        concat_dds.append({"dd_data_set": entry})

    return {"dd_concat": {"dd_name": dd_name, "dds": concat_dds}}


def _map_disp_action(action: str) -> str:
    """Map JCL disposition action to Ansible."""
    mapping = {
        "CATLG": "catalog",
        "CATALOG": "catalog",
        "UNCATLG": "uncatalog",
        "UNCATALOG": "uncatalog",
        "DELETE": "delete",
        "KEEP": "keep",
        "PASS": "keep",
    }
    return mapping.get(action.upper(), action.lower())


def _resolve_symbols(value: str, symbols: dict[str, str]) -> str:
    """Resolve symbolic parameters in a value."""
    if not value or not symbols:
        return value

    result = value
    for sym, replacement in symbols.items():
        result = result.replace(f"&{sym}.", replacement)
        result = result.replace(f"&{sym}", replacement)

    return result
