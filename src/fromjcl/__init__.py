# SPDX-License-Identifier: Apache-2.0
"""fromjcl: parse IBM z/OS JCL and serialize it to JSON, YAML, CSV, or JCL.

The public API is the set of names re-exported here. Anything reached via
`fromjcl._*` or `fromjcl.converters.*` is internal and may change without
a deprecation cycle.

Forward path::

    from fromjcl import parse, Job, to_yaml
    job = Job.from_parsed(parse("test.jcl"))
    print(to_yaml(job))

Reverse path (lossy, no byte-exact)::

    from fromjcl import from_dump
    print(from_dump(open("job.yaml").read(), "yaml"))

Byte-exact roundtrip (preserves comments, column layout, blank lines)::

    from fromjcl import parse, to_jcl
    print(to_jcl(parse("test.jcl")))
"""

from fromjcl.models import DCB, DD, Dataset, Disposition, Job, Space, Step
from fromjcl.parser import parse, parse_bytes
from fromjcl.rejcl import convert as from_dump
from fromjcl.serialize.csv import convert as to_csv
from fromjcl.serialize.jcl import convert as to_jcl
from fromjcl.serialize.json import convert as to_json
from fromjcl.serialize.raw import convert as to_raw
from fromjcl.serialize.yaml import convert as to_yaml

__all__ = [
    "parse",
    "parse_bytes",
    "Job",
    "Step",
    "DD",
    "Dataset",
    "Disposition",
    "Space",
    "DCB",
    "to_json",
    "to_yaml",
    "to_csv",
    "to_jcl",
    "to_raw",
    "from_dump",
]
