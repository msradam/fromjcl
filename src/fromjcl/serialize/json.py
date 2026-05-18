# SPDX-License-Identifier: Apache-2.0
"""Render a Job as indented JSON."""

import json as _json

from fromjcl.models import Job
from fromjcl.serialize import remove_nulls


def convert(job: Job) -> str:
    """Return the job as a JSON string with null/false/empty fields stripped."""
    return _json.dumps(remove_nulls(job.to_dict()), indent=2, default=str)
