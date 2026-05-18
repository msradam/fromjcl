"""Render a Job as block-style YAML."""

import yaml as _yaml

from fromjcl.models import Job
from fromjcl.serialize import remove_nulls


def _str_representer(dumper: _yaml.Dumper, data: str) -> _yaml.ScalarNode:
    """Use block-scalar style (|) for multiline strings."""
    if "\n" in data:
        return dumper.represent_scalar("tag:yaml.org,2002:str", data, style="|")
    return dumper.represent_scalar("tag:yaml.org,2002:str", data)


def convert(job: Job) -> str:
    """Return the job as a YAML string with null/false/empty fields stripped."""
    _yaml.add_representer(str, _str_representer)
    return _yaml.dump(remove_nulls(job.to_dict()), default_flow_style=False, sort_keys=False)
