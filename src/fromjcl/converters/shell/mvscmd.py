# SPDX-License-Identifier: Apache-2.0
"""Convert JCL steps to mvscmd shell commands."""

from fromjcl.converters.common import build_mvscmd_command
from fromjcl.converters.shell import _scaffold
from fromjcl.models import Job


def convert(job: Job) -> str:
    """Render the job as an mvscmd or mvscmdauth shell script."""
    return _scaffold.emit(job, build_mvscmd_command, header_tag="mvscmd")
