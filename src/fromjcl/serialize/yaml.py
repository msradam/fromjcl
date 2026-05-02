"""Render a Job as block-style YAML."""

import yaml as _yaml

from fromjcl.models import Job
from fromjcl.serialize import remove_nulls


def convert(job: Job) -> str:
    """Return the job as a YAML string with null/false/empty fields stripped."""
    return _yaml.dump(remove_nulls(job.to_dict()), default_flow_style=False, sort_keys=False)
