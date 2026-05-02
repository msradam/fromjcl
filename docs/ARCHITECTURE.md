# Architecture

## Pipeline

```
JCL file -> parse() -> Job model -> serializer -> output
```

1. **Parse**: `parser.py` calls the pure-Python scanner in `_scanner.py`,
   which is a port of Mike Fulton's JCLParser scanner. Returns a complete
   scan tree with column metadata and raw record bytes for byte-exact
   roundtrip.
2. **Model**: `Job.from_parsed()` builds a typed dataclass tree
   (`Job` -> `Step` -> `DD` -> `Dataset`).
3. **Serialize**: each module under `serialize/` walks either the raw
   parse tree (for byte-exact JCL output) or the `Job` model (for
   JSON/YAML/CSV) and emits text.

## Module map

```
src/fromjcl/
├── _scanner.py               pure-Python JCL scanner (port of MikeFultonDev/JCLParser)
├── parser.py                 parse(path) entry point
├── models.py                 Job, Step, DD, Dataset, Disposition, Space, DCB
├── cli.py                    argparse entry point
└── serialize/
    ├── raw.py                raw scan tree as JSON
    ├── json.py               Job as cleaned JSON
    ├── yaml.py               Job as cleaned block-style YAML
    ├── csv.py                tabular CSV view
    └── jcl.py                byte-exact JCL roundtrip emitter
```

## Roundtrip guarantee

`parse()` retains column metadata and raw record bytes so
`serialize.jcl.convert(parse(x)) == x` byte-for-byte. The sample
corpus in `tests/jcl_samples/` exercises this on every commit via
`tests/test_parser_roundtrip.py` and `tests/test_full_matrix.py`.

## Public API

```python
from fromjcl import parse, Job

job = Job.from_parsed(parse("job.jcl"))
```
